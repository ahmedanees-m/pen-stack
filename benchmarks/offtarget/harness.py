"""Off-Target-Bench (v6.10 PEN-OFFTGT, E-WS1), the nomination track for the Genome-Writing Challenge.

Scores a predictor on the immunogenic question of off-target NOMINATION: given a canonical Cas9 guide and its
candidate sites (real, published, validated-off-target labels from GUIDE-seq / CIRCLE-seq), rank the candidates so
the validated off-targets surface first. The PEN-OFFTGT engine must BEAT a sequence-homology baseline (mismatch
count). The headline numbers (`offtarget_data.BENCH_SUMMARY`) are computed on the FULL real data on the VM with the
licensed CRISOT predictor; this harness re-derives the relative comparison on the committed, CI-safe fixture (real
sites + cached CRISOT scores; the CC-BY-NC predictor is never redistributed).

Splits are held-out-GUIDE (a guide's candidates never straddle train/test) and per-assay provenance is carried.
"""
from __future__ import annotations

from pen_stack.wgenome.offtarget_data import ASSAY_PROVENANCE, BENCH_SUMMARY, bench_records


def _auprc(labels: list[int], scores: list[float]) -> float | None:
    """Average precision (area under PR), higher score = more positive."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    y = [labels[i] for i in order]
    P = sum(y)
    if P == 0:
        return None
    tp = fp = 0
    ap = 0.0
    prev = 0.0
    for yi in y:
        if yi:
            tp += 1
        else:
            fp += 1
        rec = tp / P
        prec = tp / (tp + fp)
        ap += prec * (rec - prev)
        prev = rec
    return ap


def run() -> dict:
    """Re-derive the CRISOT-vs-homology nomination comparison on the committed fixture, per assay, held-out-guide;
    report it alongside the cached full-data headline. ``available=False`` if the fixture is absent (bare wheel)."""
    rows = bench_records()
    if not rows:
        return {"available": False, "note": "Off-Target-Bench fixture absent (data tree not present)",
                "full_data": BENCH_SUMMARY}
    per_assay = {}
    for assay in sorted({r["assay"] for r in rows}):
        ar = [r for r in rows if r["assay"] == assay]
        crisot_aps, hom_aps, guides = [], [], []
        for guide in sorted({r["guide"] for r in ar}):
            gr = [r for r in ar if r["guide"] == guide]
            labels = [r["active"] for r in gr]
            if sum(labels) == 0:
                continue
            ca = _auprc(labels, [r["crisot_score"] for r in gr])
            ha = _auprc(labels, [-r["mismatch"] for r in gr])
            if ca is None or ha is None:
                continue
            crisot_aps.append(ca)
            hom_aps.append(ha)
            guides.append(guide)
        if not crisot_aps:
            continue
        mc = sum(crisot_aps) / len(crisot_aps)
        mh = sum(hom_aps) / len(hom_aps)
        per_assay[assay] = {
            "provenance": ASSAY_PROVENANCE.get(assay), "n_guides": len(guides),
            "fixture_mean_crisot_auprc": round(mc, 4), "fixture_mean_homology_auprc": round(mh, 4),
            "fixture_crisot_ge_homology": bool(mc >= mh)}
    bench_assays = ("guideseq", "circleseq", "changeseq", "siteseq")
    return {"available": True, "held_out": "guide", "assays": per_assay,
            "full_data": BENCH_SUMMARY,
            "crisot_beats_homology": all(BENCH_SUMMARY[a]["crisot_beats_homology"] for a in bench_assays),
            "n_assays": len(bench_assays),
            "note": ("fixture re-derivation (inactives downsampled, CI-safe), the AUTHORITATIVE numbers are the "
                     "full-data BENCH_SUMMARY computed on the VM across 4 unbiased assays (GUIDE/CIRCLE-seq "
                     "canonical guides; CHANGE/SITE-seq independent broad panels); a nominated off-target is a "
                     "candidate, not a clearance.")}
