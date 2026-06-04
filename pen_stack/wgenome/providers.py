"""External sequence-to-function providers (v3.1, WS-C).

AlphaGenomeProvider wraps Google DeepMind's AlphaGenome (free, non-commercial) behind a small, cached,
provider-agnostic interface so the rest of PEN-STACK never imports `alphagenome` directly. It supplies:

  * tracks(interval, outputs, ontology)  -> per-base predictions (ATAC/DNASE/RNA_SEQ/CHIP_HISTONE/...)
  * expression(interval, ontology)       -> scalar endogenous expression proxy (mean RNA_SEQ over interval)
  * contact_map(interval)                -> predicted Hi-C contact matrix (3D structural-risk feature, WS-C2)

Design rules (match the rest of the stack):
  * The LLM and the provider are NON-load-bearing for reproducibility - every cached value is keyed by an
    explicit (assembly, interval, output, ontology) tuple and written to disk, so a run is reproducible
    offline from the cache without re-querying the API.
  * The API key is read from env (ALPHAGENOME_API_KEY) or a gitignored file; NEVER committed.
  * `alphagenome` is an optional dependency. If the package or key is absent, `available()` is False and the
    dependent baselines (WS-B1, WS-C) report `pending` rather than crashing - the core stack is unaffected.

Caching: predictions are large (up to ~1M rows). We cache the *reduced* features we actually consume
(scalar expression, mean track signal, contact-map summary statistics) as small JSON/parquet, not the raw
1 Mb tensors, keyed by a content hash of the request.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CACHE = _ROOT / "data" / "alphagenome_cache"
_KEY_FILE = _ROOT / "configs" / "alphagenome_api_key.txt"
_KEY_ENV = "ALPHAGENOME_API_KEY"

# 1 Mb is AlphaGenome's max; expression/structural features use it for full regulatory context.
SEQ_LEN_1MB = 1_048_576

# Model version recorded in track-cache keys + artifacts (C1 reproducibility). Bump when the served model
# changes so stale predictions are not silently reused.
MODEL_VERSION = "alphagenome-2025-06"

# The seven measured-atlas tracks and their AlphaGenome sources. The five histone marks come from the single
# CHIP_HISTONE output selected by its `histone_mark` metadata column.
_HISTONES = ["H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]
TRACK_NAMES = ["atac", "dnase", *_HISTONES]

# K562 / HepG2 cell-type ontologies (verified against AlphaGenome human output_metadata).
CT_ONTOLOGY = {"k562": "EFO:0002067", "hepg2": "EFO:0001187"}


def _resolve_key() -> str | None:
    """API key from env first, then a gitignored file. Returns None if neither is present."""
    k = os.environ.get(_KEY_ENV)
    if k:
        return k.strip()
    if _KEY_FILE.exists():
        for line in _KEY_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip().rstrip('",; ')
            if s and not s.lower().startswith("alphagenome") and len(s) > 20:
                return s
    return None


def package_available() -> bool:
    try:
        import alphagenome  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _cache_key(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:24]


class AlphaGenomeProvider:
    """Cached wrapper around AlphaGenome's dna_client. Construct with `AlphaGenomeProvider()`."""

    def __init__(self, api_key: str | None = None, assembly: str = "hg38", cache_dir: Path = _CACHE):
        self.assembly = assembly
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._key = api_key or _resolve_key()
        self._model = None  # lazily created on first live call

    # -- availability ------------------------------------------------------
    def available(self) -> bool:
        """True when both the package and a key are present (a live call is possible)."""
        return package_available() and self._key is not None

    def _client(self):
        if self._model is None:
            from alphagenome.models import dna_client
            self._model = dna_client.create(self._key)
        return self._model

    # -- cache helpers -----------------------------------------------------
    def _load(self, key: str):
        f = self.cache_dir / f"{key}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        return None

    def _store(self, key: str, value: dict) -> None:
        (self.cache_dir / f"{key}.json").write_text(json.dumps(value, default=str), encoding="utf-8")

    # -- features ----------------------------------------------------------
    def expression(self, chrom: str, start: int, end: int, ontology: str, organism: str = "human",
                   center_bp: int = 20_000, offline: bool = False) -> dict:
        """Scalar endogenous-expression proxy: mean predicted RNA_SEQ in a central window (cached).

        The 1 Mb model context is needed for regulatory reach, but the proxy averages only the central
        `center_bp` (host-locus expression at the integration site) rather than the whole 1 Mb, which would
        wash out the local signal.
        """
        key = _cache_key("expr", self.assembly, organism, chrom, start, end, ontology, center_bp)
        hit = self._load(key)
        if hit is not None:
            return hit
        if offline:
            return {"available": False, "reason": "offline: not in cache", "key": key}
        if not self.available():
            return {"available": False, "reason": "alphagenome package or key absent", "key": key}
        from alphagenome.data import genome
        from alphagenome.models import dna_client
        org = (dna_client.Organism.MUS_MUSCULUS if organism == "mouse"
               else dna_client.Organism.HOMO_SAPIENS)
        interval = genome.Interval(chromosome=chrom, start=start, end=end).resize(SEQ_LEN_1MB)
        out = self._client().predict_interval(
            interval=interval, organism=org,
            requested_outputs=[dna_client.OutputType.RNA_SEQ], ontology_terms=[ontology])
        import numpy as np
        arr = np.asarray(out.rna_seq.values)            # (1_048_576, n_tracks)
        mid = arr.shape[0] // 2
        half = max(1, center_bp // 2)
        central = arr[max(0, mid - half):mid + half]
        rec = {"available": True, "rna_seq_mean": float(central.mean()),
               "rna_seq_max": float(central.max()), "center_bp": center_bp,
               "chrom": chrom, "start": start, "end": end,
               "ontology": ontology, "organism": organism, "key": key}
        self._store(key, rec)
        return rec

    def tracks(self, chrom: str, bin: int, ct: str, bin_size: int = 1000, center_bp: int = 1000,
               offline: bool = False) -> dict:
        """Predicted values of the seven measured-atlas tracks at a 1 kb bin (central-window mean, cached).

        `ct` is "k562" or "hepg2"; the bin centre is `bin*bin_size + bin_size/2`, predicted in 1 Mb context.
        Returns {atac, dnase, H3K27ac, H3K4me1, H3K4me3, H3K9me3, H3K27me3, model_version, ...}.
        """
        ontology = CT_ONTOLOGY.get(ct.lower(), ct)
        key = _cache_key("tracks", self.assembly, MODEL_VERSION, chrom, bin, ontology, bin_size, center_bp)
        hit = self._load(key)
        if hit is not None:
            return hit
        if offline:
            return {"available": False, "reason": "offline: not in cache", "key": key}
        if not self.available():
            return {"available": False, "reason": "alphagenome package or key absent", "key": key}
        import numpy as np
        from alphagenome.data import genome
        from alphagenome.models import dna_client
        pos = bin * bin_size + bin_size // 2
        interval = genome.Interval(chromosome=chrom, start=pos, end=pos).resize(SEQ_LEN_1MB)
        out = self._client().predict_interval(
            interval=interval,
            requested_outputs=[dna_client.OutputType.ATAC, dna_client.OutputType.DNASE,
                               dna_client.OutputType.CHIP_HISTONE],
            ontology_terms=[ontology])

        def central(values) -> np.ndarray:
            arr = np.asarray(values)
            mid = arr.shape[0] // 2
            half = max(1, center_bp // 2)
            return arr[max(0, mid - half):mid + half]

        rec = {"available": True, "chrom": chrom, "bin": int(bin), "ct": ct, "ontology": ontology,
               "model_version": MODEL_VERSION, "center_bp": center_bp, "key": key,
               "atac": float(central(out.atac.values).mean()),
               "dnase": float(central(out.dnase.values).mean())}
        ch = out.chip_histone
        md, vals = ch.metadata.reset_index(drop=True), central(ch.values)
        for mark in _HISTONES:
            cols = md.index[md["histone_mark"] == mark].to_numpy()
            rec[mark] = float(vals[:, cols].mean()) if len(cols) else float("nan")
        self._store(key, rec)
        return rec

    def contact_map_summary(self, chrom: str, start: int, end: int, ontology: str) -> dict:
        """3D structural-risk summary (WS-C2): variance + mean of the predicted contact map (cached)."""
        key = _cache_key("contact", self.assembly, chrom, start, end, ontology)
        hit = self._load(key)
        if hit is not None:
            return hit
        if not self.available():
            return {"available": False, "reason": "alphagenome package or key absent", "key": key}
        from alphagenome.data import genome
        from alphagenome.models import dna_client
        interval = genome.Interval(chromosome=chrom, start=start, end=end).resize(SEQ_LEN_1MB)
        out = self._client().predict_interval(
            interval=interval, requested_outputs=[dna_client.OutputType.CONTACT_MAPS],
            ontology_terms=[ontology])
        import numpy as np
        m = np.asarray(out.contact_maps.values)
        rec = {"available": True, "contact_mean": float(m.mean()), "contact_var": float(m.var()),
               "chrom": chrom, "start": start, "end": end, "ontology": ontology, "key": key}
        self._store(key, rec)
        return rec


class MeasuredTrackProvider:
    """The existing measured-ENCODE backbone: reads `phase_1/features/chromatin_{ct}.parquet` per bin.

    Same `tracks()` signature as AlphaGenomeProvider so C2 can compare predicted vs measured on identical
    bins, and so downstream code can swap providers without branching.
    """

    _P1 = _ROOT.parent / "phase_1" / "features"

    def __init__(self, ct: str):
        import pandas as pd
        self.ct = ct.lower()
        self._df = pd.read_parquet(self._P1 / f"chromatin_{self.ct}.parquet").set_index(["chrom", "bin"])

    def available(self) -> bool:
        return True

    def tracks(self, chrom: str, bin: int, ct: str | None = None, **_: object) -> dict:
        try:
            row = self._df.loc[(chrom, int(bin))]
        except KeyError:
            return {"available": False, "reason": "bin not in measured grid"}
        return {"available": True, "chrom": chrom, "bin": int(bin), "ct": self.ct,
                **{t: float(row[t]) for t in TRACK_NAMES if t in row}}


def smoke() -> dict:
    """Lightweight readiness probe used by tests/CLI - reports availability without a live call."""
    p = AlphaGenomeProvider()
    return {"package_available": package_available(), "key_present": _resolve_key() is not None,
            "available": p.available(), "model_version": MODEL_VERSION, "track_names": TRACK_NAMES,
            "cache_dir": str(_CACHE)}


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(smoke(), indent=2))
