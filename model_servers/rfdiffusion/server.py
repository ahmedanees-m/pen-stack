"""RFdiffusion model server (PEN-STACK live oracle, local GPU).

A tiny FastAPI wrapper around RFdiffusion (RosettaCommons/RFdiffusion) so the pen_stack oracle adapter can call
a REAL protein-backbone generator over localhost. The adapter (`oracles/protein_design.py::generate_backbone`)
POSTs a length/contig spec here and gets back a generated backbone PDB; when the service is down the adapter
defers (never fabricates). The backbone is a CANDIDATE (it must pass writer-verification before any claim).

Runs in the rfdiffusion:base image (torch 1.12, the vendored SE3-Transformer env). Weights are mounted at
/models. Run: uvicorn server:app --host 0.0.0.0 --port 9013
"""
from __future__ import annotations

import glob
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException

RFD_DIR = os.getenv("RFDIFFUSION_DIR", "/app/RFdiffusion")
MODELS = os.getenv("RFDIFFUSION_MODELS", "/models")
app = FastAPI(title="RFdiffusion model server", version="1.0")


@app.get("/health")
def health() -> dict:
    import torch
    ok = Path(RFD_DIR, "scripts", "run_inference.py").exists()
    weights = sorted(os.path.basename(p) for p in glob.glob(f"{MODELS}/*.pt"))
    return {"status": "ok" if (ok and weights) else "missing", "model": "rfdiffusion",
            "cuda": torch.cuda.is_available(), "weights": weights,
            "device": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")}


@app.post("/generate")
def generate(req: dict) -> dict:
    """Body: {length?: int (unconditional monomer), contigs?: str (RFdiffusion contig map), num_designs?: 1}.
    Returns {designs: [{pdb, n_residues}], n, backend}. Each backbone is a CANDIDATE."""
    req = req or {}
    contigs = req.get("contigs")
    if not contigs:
        length = int(req.get("length", 0))
        if length <= 0:
            raise HTTPException(422, "provide 'length' (>0) or a 'contigs' string")
        contigs = f"{length}-{length}"
    n = int(req.get("num_designs", 1))
    with tempfile.TemporaryDirectory() as td:
        prefix = str(Path(td, "design"))
        cmd = ["python3.9", f"{RFD_DIR}/scripts/run_inference.py",
               f"inference.output_prefix={prefix}", f"inference.model_directory_path={MODELS}",
               f"inference.num_designs={n}", f"contigmap.contigs=[{contigs}]"]
        proc = subprocess.run(cmd, cwd=RFD_DIR, capture_output=True, text=True,
                              timeout=int(os.getenv("RFD_TIMEOUT", "1200")))
        pdbs = sorted(glob.glob(f"{prefix}_*.pdb"))
        if not pdbs:
            raise HTTPException(500, f"rfdiffusion produced no PDB: {(proc.stderr or proc.stdout)[-400:]}")
        designs = []
        for p in pdbs:
            text = Path(p).read_text(encoding="utf-8")
            n_res = len({ln[22:27] for ln in text.splitlines() if ln.startswith("ATOM") and ln[12:16].strip() == "CA"})
            designs.append({"pdb": text, "n_residues": n_res})
    return {"designs": designs, "n": len(designs), "backend": "rfdiffusion", "contigs": contigs}
