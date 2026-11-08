#!/usr/bin/env python3
"""Rebuild benchmarks/position_effect_human/leemans_scored_input.parquet from its two upstream sources.

The table is not redistributed here. Every column in it is published by Leemans et al. (2019), in two
places, and this script fetches both and joins them on the reporter barcode:

  features, expression, LAD call, promoter name and escaper/repressed class
      github.com/vansteensellab/Promoters_in_LADs
        -> data/cl20181013_feature_set_trip.Rdata     objects X (9,298 x 32), y, lad_vec

  per-barcode integration coordinates (hg19)
      Cell supplement Dataset S2, served by Europe PMC for the open-access record
        -> .../PMC6506275/supplementaryFiles -> mmc4.zip -> Dataset_S2_TRIP.tsv   (12,812 rows)

The 9,298 rows are the row count of the authors' own feature matrix, not a filter applied here; the
barcode join to the coordinate table is exact at 9,298 of 9,298. The only contribution of this script
is that join and the selection of five of their fourteen marks.

Coordinates are hg19, as the upstream supplement states. Nothing downstream cross-references them to
an hg38 annotation: resolution_ablation.py bins on `pos`, which is build-agnostic, and
p2_build_human_head.py does not read it.

Needs `pyreadr` to read the R data file:  pip install pyreadr

Usage
    python scripts/build_leemans_input.py                 # fetch both sources and write the parquet
    python scripts/build_leemans_input.py --check         # rebuild and compare, write nothing
    python scripts/build_leemans_input.py --rdata F.Rdata --supplement mmc4.zip
                                                          # use local copies instead of fetching

A fetched source is cached under data/external/leemans_sources/ (gitignored), so a rebuild does not
download it again. PEN_LEEMANS_CACHE relocates that directory; an empty value fetches every time.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "position_effect_human" / "leemans_scored_input.parquet"

RDATA_URL = ("https://raw.githubusercontent.com/vansteensellab/Promoters_in_LADs/"
             "HEAD/data/cl20181013_feature_set_trip.Rdata")
SUPP_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6506275/supplementaryFiles"

# the five marks this axis uses, out of the fourteen the authors publish
MARKS = ["H3K27ac_mean", "H3K4me1_mean", "H3K9me3_mean", "H3K27me3_mean", "H3K36me3_mean"]
COLUMNS = ["barcode", "chrom", "pos"] + MARKS + ["LMNB1_DamID", "prom_name", "class", "expr_y", "lad"]

# content digest of the table this script reproduces, over the canonical CSV rendering below
EXPECTED_CONTENT_SHA256 = "2662adf8f2c39a934a2d326ecb32b73b5607ee1a50ac4c667687ffd73c64e9c0"


# HTTP statuses worth another attempt; anything else is reported as it is.
_RETRY_STATUS = (408, 425, 429, 500, 502, 503, 504)
# Exit code for "the upstream source could not be reached". Callers use it to treat the result as
# data-gated rather than as a reproduction failure.
EXIT_SOURCE_UNAVAILABLE = 3
# A fetched source is kept here so a rebuild does not download it again. The directory is
# gitignored, so nothing upstream is redistributed. Set PEN_LEEMANS_CACHE to another directory, or
# to an empty value to fetch every time.
_CACHE_DEFAULT = ROOT / "data" / "external" / "leemans_sources"


def _cache_path(url: str) -> Path | None:
    loc = os.environ.get("PEN_LEEMANS_CACHE", str(_CACHE_DEFAULT))
    if not loc:
        return None
    return Path(loc) / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] + ".bin")


def _describe(data: bytes) -> str:
    """A short, readable account of a body that is not what was asked for."""
    head = data[:300]
    try:
        text = head.decode("utf-8").strip()
    except UnicodeDecodeError:
        return "%d bytes, not text" % len(data)
    return "%d bytes: %s" % (len(data), " ".join(text.split())[:200])


def _get(url: str, timeout: int = 600, attempts: int = 5, *,
         magic: bytes | None = None, min_bytes: int = 1024) -> bytes:
    """Fetch a URL, reusing a local copy when there is one and retrying a bad response.

    Two things have to be tolerated. A partial chunked response raises
    http.client.IncompleteRead, so one attempt is not enough even from a healthy source. And the
    supplement endpoint can answer 200 with a short XML error document instead of the archive, so
    the body is checked against `magic` and `min_bytes` rather than merely being non-empty.

    Exits with EXIT_SOURCE_UNAVAILABLE when every attempt fails, so a caller can tell a
    third-party outage apart from a reproduction failure.
    """
    cache = _cache_path(url)
    if cache is not None and cache.is_file() and cache.stat().st_size >= min_bytes:
        return cache.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "pen-stack-build-leemans"})
    last = ""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if len(data) < min_bytes or (magic is not None and not data.startswith(magic)):
                last = "the response is not the expected payload (%s)" % _describe(data)
            else:
                if cache is not None:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_bytes(data)
                return data
        except urllib.error.HTTPError as e:
            last = "HTTP %d %s" % (e.code, e.reason)
            if e.code not in _RETRY_STATUS:
                print("[fail] %s: %s" % (url, last), file=sys.stderr)
                raise SystemExit(EXIT_SOURCE_UNAVAILABLE)
        except (http.client.HTTPException, OSError) as e:
            last = "%s: %s" % (type(e).__name__, e)
        if attempt < attempts:
            wait = 2 ** attempt
            print("[retry %d/%d] %s: %s; waiting %ds" % (attempt, attempts, url, last, wait),
                  file=sys.stderr)
            time.sleep(wait)
    print("[unavailable] %s could not be fetched in %d attempts: %s" % (url, attempts, last),
          file=sys.stderr)
    raise SystemExit(EXIT_SOURCE_UNAVAILABLE)


def load_features(path: Path | None) -> pd.DataFrame:
    """X, y and lad_vec from the authors' feature set, keyed by barcode."""
    try:
        import pyreadr
    except ImportError:  # pragma: no cover - environment-dependent
        sys.exit("pyreadr is required to read the upstream R data file: pip install pyreadr")
    raw = path.read_bytes() if path else _get(RDATA_URL)
    tmp = Path(__file__).resolve().parent / "_leemans_features.Rdata"
    tmp.write_bytes(raw)
    try:
        r = pyreadr.read_r(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)
    X, y, lad = r["X"], r["y"], r["lad_vec"]
    df = X.copy()
    df["barcode"] = [str(i) for i in X.index]
    df["expr_y"] = y.iloc[:, 0].to_numpy()
    df["lad"] = lad.iloc[:, 0].astype(str).to_numpy()
    return df.reset_index(drop=True)


def load_coordinates(path: Path | None) -> pd.DataFrame:
    """seqname and position per barcode, from Dataset S2 of the supplement."""
    if path:
        outer = None
        inner = zipfile.ZipFile(path)
    else:
        outer = zipfile.ZipFile(io.BytesIO(_get(SUPP_URL, magic=b"PK\x03\x04")))
        inner = zipfile.ZipFile(io.BytesIO(outer.read("mmc4.zip")))
    tsv = inner.read("Dataset_S2_TRIP.tsv")
    s2 = pd.read_csv(io.BytesIO(tsv), sep="\t", low_memory=False)
    return s2[["barcode", "seqname", "position"]].rename(
        columns={"seqname": "chrom", "position": "pos"})


def build(rdata: Path | None = None, supplement: Path | None = None) -> pd.DataFrame:
    feats = load_features(rdata)
    coords = load_coordinates(supplement)
    n_feat = len(feats)
    merged = feats.merge(coords, on="barcode", how="inner", validate="one_to_one")
    if len(merged) != n_feat:
        sys.exit("barcode join is not exact: %d feature rows, %d joined" % (n_feat, len(merged)))
    out = merged[COLUMNS].copy()
    out["chrom"] = out["chrom"].astype(str)
    out["pos"] = out["pos"].astype("int64")
    for c in MARKS + ["LMNB1_DamID", "expr_y"]:
        out[c] = out[c].astype(float)
    for c in ("barcode", "prom_name", "class", "lad"):
        out[c] = out[c].astype(str)
    return out


def content_sha256(df: pd.DataFrame) -> str:
    """Digest of the values, not the file bytes, so it is stable across parquet writers.

    Floats are rounded to 10 decimals first. The R -> Python -> parquet round trip moves the last
    bit of a float64, so an unrounded digest would reject a correct rebuild over 1e-16 of noise.
    """
    canon = df[COLUMNS].sort_values("barcode", kind="mergesort").reset_index(drop=True)
    import numpy as np
    with np.errstate(invalid="ignore"):          # 15 rows have no upstream chromatin signal
        for c in canon.columns:
            if canon[c].dtype.kind == "f":
                canon[c] = canon[c].round(10)
    buf = io.StringIO()
    canon.to_csv(buf, index=False, float_format="%.10f", lineterminator="\n")
    return hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rdata", type=Path, help="local copy of cl20181013_feature_set_trip.Rdata")
    ap.add_argument("--supplement", type=Path, help="local copy of mmc4.zip")
    ap.add_argument("--check", action="store_true", help="rebuild and compare only, write nothing")
    a = ap.parse_args()

    df = build(a.rdata, a.supplement)
    digest = content_sha256(df)
    print("[built] %d rows x %d cols  content sha256 %s" % (len(df), len(df.columns), digest))

    if EXPECTED_CONTENT_SHA256 != "PLACEHOLDER":
        if digest != EXPECTED_CONTENT_SHA256:
            print("[fail] content digest does not match the recorded one:\n  expected %s\n  got      %s"
                  % (EXPECTED_CONTENT_SHA256, digest), file=sys.stderr)
            return 1
        print("[ok] content digest matches the recorded one")

    if a.check:
        if OUT.exists():
            have = content_sha256(pd.read_parquet(OUT))
            print("[compare] on-disk table content sha256 %s  %s"
                  % (have, "identical" if have == digest else "DIFFERS"))
            return 0 if have == digest else 1
        print("[compare] %s is absent; nothing to compare against" % OUT.name)
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print("[wrote] %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
