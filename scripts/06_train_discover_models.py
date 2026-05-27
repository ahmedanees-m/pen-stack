"""Train PEN-DISCOVER gate-probability models on ESM-2 embeddings.

Corrections vs execution plan:
- pen_score.api.Scorer().score_editor(eid) is correct API (not score())
- AxisScores uses attribute access: result.axes.S_DSB (not dict indexing)
- S_DSB=None for DSB-free recombinases (IS110, recombinases) -> assign 1.0
- certify() returns TrueWriterResult with .gate_results (tuple of GateResult)
- GateResult.gate_id, GateResult.passes
- load_editor_universe() returns list[EditorEntry], not object with .editors
"""
import sys, warnings
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, "/workspace/pen-stack")

from pen_stack.discover.predictor import DiscoverPredictor
from pen_score.api import Scorer
from pen_score import get_editor_metadata
from pen_score.data.loader import load_editor_universe
from pen_stack.compare.certify import certify

# DSB-free mechanism buckets (S_DSB should be 1.0)
DSB_FREE_MECHANISMS = {"DSB_FREE_TRANSEST_RECOMBINASE", "TRANSPOSASE"}

# Tier -> tw_probability mapping
TIER_TO_TW = {
    "TRUE_WRITER": 1.0,
    "PROBABLE_WRITER": 0.75,
    "EMERGING_WRITER": 0.4,
    "NOT_WRITER": 0.05,
}

# Load embeddings
emb_df = pd.read_parquet("data/esm2_embeddings.parquet")
print(f"Loaded embeddings: {emb_df.shape}")
print(f"Editors in embeddings: {emb_df.editor_id.tolist()}")
print()

# Load editor universe for mechanism bucket lookup
editors = load_editor_universe()
editor_map = {e.id: e for e in editors}

# Build gate labels from pen-score certifications
scorer = Scorer()
rows = []
for _, row in emb_df.iterrows():
    eid = row["editor_id"]
    try:
        score_result = scorer.score_editor(eid)
        md = get_editor_metadata(eid)
        e = editor_map.get(eid)

        # Determine S_DSB
        s_dsb = score_result.axes.S_DSB
        if s_dsb is None:
            if e and e.mechanism_bucket in DSB_FREE_MECHANISMS:
                s_dsb = 1.0   # DSB-free recombinase: perfect DSB avoidance
            else:
                s_dsb = 0.5   # unknown

        # Determine S_Prog (programmability)
        s_prog = score_result.axes.S_Prog
        if s_prog is None:
            s_prog = 0.0

        # Determine S_Cargo
        s_cargo = score_result.axes.S_Cargo
        if s_cargo is None:
            s_cargo = 0.0

        # Evidence sources
        evidence_sources = ["biochemical"]
        if md.cell_based_evidence:
            evidence_sources.append("cell_based")
        if getattr(md, "has_structural", False):
            evidence_sources.append("structural")

        # Certify
        cert = certify(
            editor_id=eid,
            s_dsb=float(s_dsb),
            s_prog=float(s_prog),
            s_cargo=float(s_cargo),
            length_aa=int(row["length_aa"]),
            evidence_sources=evidence_sources,
            intrinsic_cargo_mechanism=bool(md.intrinsic_cargo_mechanism),
        )

        # Parse gate results (gate_id -> passes)
        gate_dict = {gr.gate_id: bool(gr.passes) for gr in cert.gate_results}

        # TW probability: tier-based with auto-demote handling
        tier_prob = TIER_TO_TW.get(cert.tier, 0.05)
        n_qualifying = len([g for g in cert.gate_results if g.gate_id != "gate_1_dsb"])
        q_frac = cert.qualifying_gates_passed / max(1, n_qualifying)
        if cert.tier == "NOT_WRITER" and cert.auto_demoted:
            # Auto-demoted due to necessary gate failure, but qualifying passes matter
            tw_prob = q_frac * 0.2
        else:
            tw_prob = tier_prob

        rows.append({
            "editor_id": eid,
            "gate_1_dsb": gate_dict.get("gate_1_dsb", False),
            "gate_2_prog": gate_dict.get("gate_2_prog", False),
            "gate_3_cargo": gate_dict.get("gate_3_cargo", False),
            "gate_4_deliv": gate_dict.get("gate_4_deliv", False),
            "gate_5_evidence": gate_dict.get("gate_5_evidence", False),
            "tw_probability": tw_prob,
            "tier": cert.tier,
        })
        print(f"  {eid}: tier={cert.tier}, q_passed={cert.qualifying_gates_passed}/4, tw={tw_prob:.3f}")

    except Exception as ex:
        print(f"  Skipped {eid}: {ex}")

labels_df = pd.DataFrame(rows)
print(f"\nGate labels for {len(labels_df)} editors")
print(labels_df[["editor_id", "gate_1_dsb", "gate_2_prog", "gate_3_cargo", "tw_probability", "tier"]].to_string())

# Save labels for reference
Path("data").mkdir(exist_ok=True)
labels_df.to_csv("data/discover_gate_labels.csv", index=False)
print("\nGate label distribution:")
for g in ["gate_1_dsb", "gate_2_prog", "gate_3_cargo", "gate_4_deliv", "gate_5_evidence"]:
    if g in labels_df.columns:
        pos_rate = labels_df[g].mean()
        print(f"  {g}: {pos_rate:.2f} pass rate ({int(labels_df[g].sum())}/{len(labels_df)})")

# Train
predictor = DiscoverPredictor()
predictor.train(emb_df, labels_df)

# Smoke tests
print("\n=== Smoke tests ===")
for eid_test in ["ISCro4", "IS621", "SpCas9"]:
    subset = emb_df[emb_df.editor_id == eid_test]
    if len(subset) == 0:
        print(f"{eid_test}: not in embeddings (skipping)")
        continue
    emb_vec = subset.filter(like="esm2_").values[0]
    pred = predictor.predict(emb_vec, editor_id=eid_test)
    print(f"{eid_test}: TW_prob={pred.tw_probability:.3f}, tier={pred.predicted_tier}, rec={pred.recommendation}")

print("\nTraining complete. Models saved to data/discover_models/")
