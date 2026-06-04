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


def smoke() -> dict:
    """Lightweight readiness probe used by tests/CLI - reports availability without a live call."""
    p = AlphaGenomeProvider()
    return {"package_available": package_available(), "key_present": _resolve_key() is not None,
            "available": p.available(), "cache_dir": str(_CACHE)}


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(smoke(), indent=2))
