"""Mechanism-aware classification at scale (Phase 2, Step 2.2).

Run the audited Pfam-whitelist classifier over the expanded Writer Atlas. For every system, derive a
``mech_pred`` bucket + ``mech_conf`` *independently* from its Pfam domain architecture (homology), then
compare against the inherited/audited ``mechanism_bucket`` — keeping homology and mechanism distinct, as
the program requires. Low-confidence / conflicting / disagreeing calls are written to a review queue and
flagged, never hidden.

Inputs : pen_stack/atlas/atlas.parquet, the 18-family whitelist.
Outputs: atlas.parquet updated with mech_pred / mech_conf / mech_basis / mech_agrees,
         out/mech_review_queue.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pen_stack.mech.whitelist import PfamWhitelist

_ROOT = Path(__file__).resolve().parents[2]
_ATLAS = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"
_QUEUE = _ROOT / "out" / "mech_review_queue.csv"


def classify_atlas(atlas_parquet: str | Path = _ATLAS, out: str | Path = _ATLAS,
                   queue: str | Path = _QUEUE) -> pd.DataFrame:
    atlas = pd.read_parquet(atlas_parquet)
    wl = PfamWhitelist()

    calls = atlas["pfam_signature"].apply(lambda s: wl.classify(list(s) if s is not None else []))
    atlas["mech_pred"] = [c.bucket for c in calls]
    atlas["mech_conf"] = [c.confidence for c in calls]
    atlas["mech_basis"] = [c.basis for c in calls]
    # agreement with the inherited/audited mechanism label (None where one side is missing)
    atlas["mech_agrees"] = [
        (mp == mb) if (mp is not None and pd.notna(mb)) else None
        for mp, mb in zip(atlas["mech_pred"], atlas["mechanism_bucket"])
    ]
    atlas["mech_class_version"] = wl.version

    # review queue: no domain evidence, conflicting evidence, or disagreement with the audited label
    flag = (
        atlas["mech_conf"].isin(["none", "conflicting"])
        | atlas["mech_agrees"].eq(False)   # explicit False (disagreement), not NaN
    )
    q = atlas.loc[flag, ["representative_system", "family", "pfam_signature",
                         "mechanism_bucket", "mech_pred", "mech_conf", "mech_basis",
                         "mech_agrees", "confidence"]]
    Path(queue).parent.mkdir(parents=True, exist_ok=True)
    q.to_csv(queue, index=False)

    atlas.to_parquet(out, index=False)
    return atlas


def core_agreement(atlas: pd.DataFrame) -> dict:
    """Agreement on the curated 8-family core against the audited 18-family labels."""
    core = atlas[atlas["entry_kind"] == "curated_core"]
    scored = core[core["mech_pred"].notna()]
    agree = int((scored["mech_pred"] == scored["mechanism_bucket"]).sum())
    return {"n_core": len(core), "n_scored": len(scored), "n_agree": agree,
            "agreement": round(agree / len(scored), 4) if len(scored) else None}


if __name__ == "__main__":  # pragma: no cover
    a = classify_atlas()
    print("mech_conf distribution:\n", a["mech_conf"].value_counts())
    print("\ncore agreement:", core_agreement(a))
    n_flag = int((a["mech_conf"].isin(["none", "conflicting"]) | (a["mech_agrees"].eq(False))).sum())
    print("\nreview queue rows:", n_flag)
