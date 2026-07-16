"""ProteinMPNN model server (PEN-STACK live oracle, local GPU).

A tiny FastAPI wrapper around ProteinMPNN (dauparas/ProteinMPNN) so the pen_stack oracle adapter can call a
REAL sequence-design backend over localhost, exactly like the hosted APIs, but on the VM's GPU. The adapter
(`oracles/protein_design.py::design_sequence`) HTTP-POSTs a backbone PDB here and gets back designed sequences
+ scores; when this service is down the adapter defers (never fabricates). Output is still a CANDIDATE.

Run (on the VM, in the proteinmpnn image): uvicorn server:app --host 0.0.0.0 --port 9011
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException

MPNN_DIR = os.getenv("PROTEINMPNN_DIR", "/opt/ProteinMPNN")
app = FastAPI(title="ProteinMPNN model server", version="1.0")


@app.get("/health")
def health() -> dict:
    ok = Path(MPNN_DIR, "protein_mpnn_run.py").exists()
    import torch
    return {"status": "ok" if ok else "missing_model", "model": "proteinmpnn",
            "cuda": torch.cuda.is_available(),
            "device": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")}


def _parse_fasta(fa: str) -> list[dict]:
    """ProteinMPNN seqs/*.fa: the first record is the input; subsequent records are designs with a header that
    carries `score=...` and `global_score=...`. Return [{sequence, score, global_score}]."""
    out, header, seq = [], None, []
    recs = []
    for line in fa.splitlines():
        if line.startswith(">"):
            if header is not None:
                recs.append((header, "".join(seq)))
            header, seq = line[1:], []
        else:
            seq.append(line.strip())
    if header is not None:
        recs.append((header, "".join(seq)))
    for header, s in recs[1:]: # skip record 0 (the native input sequence)
        meta = {}
        for kv in header.split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                meta[k.strip()] = v.strip()
        out.append({"sequence": s,
                    "score": float(meta["score"]) if "score" in meta else None,
                    "global_score": float(meta["global_score"]) if "global_score" in meta else None})
    return out


@app.post("/design")
def design(req: dict) -> dict:
    """Body: {pdb: <PDB text>, chains?: 'A', num_seqs?: 4, sampling_temp?: 0.1, seed?: 37}.
    Returns {designs: [{sequence, score, global_score}], n, backend}."""
    pdb = (req or {}).get("pdb")
    if not isinstance(pdb, str) or "ATOM" not in pdb:
        raise HTTPException(422, "field 'pdb' (PDB text with ATOM records) is required")
    num_seqs = int(req.get("num_seqs", 4))
    temp = float(req.get("sampling_temp", 0.1))
    seed = int(req.get("seed", 37))
    chains = req.get("chains")
    with tempfile.TemporaryDirectory() as td:
        pdb_path = Path(td, "bb.pdb")
        pdb_path.write_text(pdb, encoding="utf-8")
        out_dir = Path(td, "out")
        out_dir.mkdir()
        cmd = ["python", f"{MPNN_DIR}/protein_mpnn_run.py", "--pdb_path", str(pdb_path),
               "--out_folder", str(out_dir), "--num_seq_per_target", str(num_seqs),
               "--sampling_temp", str(temp), "--seed", str(seed), "--batch_size", "1"]
        if chains:
            cmd += ["--pdb_path_chains", str(chains)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise HTTPException(500, f"proteinmpnn failed: {proc.stderr[-400:]}")
        fa_files = list((out_dir / "seqs").glob("*.fa"))
        if not fa_files:
            raise HTTPException(500, f"no output FASTA produced: {proc.stdout[-300:]}")
        designs = _parse_fasta(fa_files[0].read_text(encoding="utf-8"))
    return {"designs": designs, "n": len(designs), "backend": "proteinmpnn", "sampling_temp": temp, "seed": seed}
