"""v3.1 WS-C - AlphaGenome integration (sequence features + 3D structural risk).

Pure-logic checks (track mapping, quantile map, insulation, bin maths, offline contract) run always and make
NO network calls. Data/API-dependent checks (measured tracks, live predictions) skip on CI.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_FEAT = Path(__file__).resolve().parents[2].parent / "phase_1" / "features"
_K562 = _FEAT / "chromatin_k562.parquet"


def test_provider_track_constants_and_ontology():
    from pen_stack.wgenome.providers import CT_ONTOLOGY, MODEL_VERSION, TRACK_NAMES
    assert TRACK_NAMES[:2] == ["atac", "dnase"]
    assert len(TRACK_NAMES) == 7                     # atac, dnase, 5 histones
    assert CT_ONTOLOGY["k562"] == "EFO:0002067" and CT_ONTOLOGY["hepg2"] == "EFO:0001187"
    assert MODEL_VERSION


def test_tracks_offline_is_cache_only_no_network():
    from pen_stack.wgenome.providers import AlphaGenomeProvider
    p = AlphaGenomeProvider(assembly="hg38")
    r = p.tracks("chrZZ", 999_999_999, "k562", offline=True)
    assert r["available"] is False and "offline" in r["reason"]


def test_quantile_map_preserves_rank_and_targets_measured_marginal():
    from pen_stack.wgenome.chromatin_seq import quantile_map
    pred = pd.Series([0.1, 5.0, 2.0, 9.0])          # arbitrary units
    meas = pd.Series([0.0, 0.0, 1.0, 3.0])          # measured marginal
    out = quantile_map(pred, meas)
    # ranking preserved, values pulled into the measured range
    assert list(np.argsort(out.to_numpy())) == list(np.argsort(pred.to_numpy()))
    assert out.max() <= meas.max() + 1e-9 and out.min() >= meas.min() - 1e-9


def test_structure3d_inserts_and_bin_maths():
    from pen_stack.wgenome import structure3d as s3
    assert len(s3.strong_enhancer_insert()) == len(s3.neutral_insert())   # length-matched (controls shift)
    assert s3.strong_enhancer_insert() != s3.neutral_insert()
    assert s3._bin_of(0) == s3.CONTACT_BINS // 2                          # centre maps to middle bin
    assert s3._bin_of(s3.SEQ_LEN_1MB // 2) > s3._bin_of(0)                # downstream offset -> higher bin


def test_insulation_score_on_synthetic_matrix():
    from pen_stack.wgenome.structure3d import insulation_score
    mat = np.ones((40, 40))
    assert insulation_score(mat, 20, w=5) == pytest.approx(1.0)
    assert np.isnan(insulation_score(mat, 0, w=5))                        # no left flank at the edge


def test_structural_risk_offline_contract():
    from pen_stack.wgenome.structure3d import structural_risk
    r = structural_risk("chr8", 127_600_000, 127_735_434, offline=True)
    assert r["available"] is False                                       # never calls API when offline


@pytest.mark.skipif(not _K562.exists(), reason="measured chromatin not present")
def test_measured_track_provider_reads_bins():
    from pen_stack.wgenome.providers import MeasuredTrackProvider
    p = MeasuredTrackProvider("k562")
    df = pd.read_parquet(_K562)
    r0 = df.iloc[0]
    rec = p.tracks(r0["chrom"], int(r0["bin"]))
    assert rec["available"] is True and "atac" in rec and "H3K27ac" in rec
