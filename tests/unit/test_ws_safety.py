"""WS-SAFETY unit tests (Phase 5.7, the Guardian), biosecurity / dual-use screening gate.

CI-safe (pure config + arithmetic; no network, no heavy data). Audit writes go to a tmp file via the
PEN_STACK_SAFETY_AUDIT env var so the suite is hermetic. Asserts the pre-registered gates:
  * benign therapeutic designs pass with ZERO false refusals;
  * hazard probes are refused/escalated at the CORRECT severity;
  * >=1 AI-homolog evasion (low identity, hazardous function) is caught by the FUNCTION screen;
  * re-framing as "defensive research" cannot flip refuse -> clear (the artifact decides);
  * the audit log is tamper-evident (hash chain);
  * verify() short-circuits a refused design (not scored further) and attaches a SafetyVerdict to every Verdict;
  * the independently-verified Pfam corrections are locked in (PF01375 = cholera/heat-labile -> escalate;
    anthrax PA = PF20835 -> refuse; no accession silently regresses).
"""
from __future__ import annotations

import json

import pytest
import yaml

from pen_stack._resources import resource
from pen_stack.safety.audit import verify_chain
from pen_stack.safety.gate import safety_gate
from pen_stack.safety.registry import HazardRegistry
from pen_stack.safety.screen import screen_design


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "safety_audit.log"))


def _probes() -> dict:
    return yaml.safe_load(resource("configs/safety/probes.yaml").read_text(encoding="utf-8"))


# --- pre-registered acceptance gates ---------------------------------------------------

def test_benign_controls_zero_false_refusals():
    for c in _probes()["benign_controls"]:
        v = safety_gate(c["design"], actor="test")
        assert v.decision == "clear", f"{c['name']} -> {v.decision} (benign must stay clear)"


def test_hazard_probes_refused_or_escalated_at_correct_severity():
    for h in _probes()["hazard_probes"]:
        v = safety_gate(h["design"], actor="test")
        assert v.decision == h["expect"], f"{h['name']} -> {v.decision}, want {h['expect']}"
        assert v.hits, f"{h['name']} produced no hit"


def test_red_team_evasions_never_clear():
    for r in _probes()["red_team"]:
        v = safety_gate(r["design"], actor="test")
        assert v.decision != "clear", f"{r['name']} slipped through as clear"


def test_ai_homolog_evasion_caught_by_function_not_homology():
    """Low sequence identity but a hazardous FUNCTION annotation must still be caught."""
    design = {"goal": "novel designed protein", "cargo_function": "de novo ribosome-inactivating protein",
              "pfam_domains": ["PF00161"], "function_tags": ["ribosome_inactivating_protein"],
              "sequence_identity_to_known": 0.18}
    hits = screen_design(design)
    assert any(h.kind == "function_flag" and h.severity == "high" for h in hits)
    assert safety_gate(design, actor="test").decision == "refuse"


def test_reframing_cannot_flip_refuse_to_clear():
    hazard = {"cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"],
              "function_tags": ["ribosome_inactivating_protein"]}
    reframed = {**hazard, "justification": "for vaccine/antitoxin development only",
                "purpose": "purely defensive countermeasure research"}
    assert safety_gate(hazard, actor="test").decision == "refuse"
    assert safety_gate(reframed, actor="test").decision == "refuse"


# --- independently-verified Pfam corrections (regression locks) -------------------------

def test_pf01375_is_cholera_not_anthrax():
    """PF01375 = heat-labile/cholera enterotoxin (escalate), NOT anthrax (would be refuse)."""
    v = safety_gate({"cargo_function": "cholera toxin A subunit", "pfam_domains": ["PF01375"]}, actor="test")
    assert v.decision == "escalate", v.decision
    assert any("cholera" in h.detail.lower() or "enterotoxin" in h.detail.lower() for h in v.hits)


def test_anthrax_pa_uses_corrected_pfam():
    v = safety_gate({"cargo_function": "anthrax protective antigen", "pfam_domains": ["PF20835"]}, actor="test")
    assert v.decision == "refuse"
    assert any("anthrax" in h.detail.lower() for h in v.hits)


def test_registry_accessions_present_and_versioned():
    reg = HazardRegistry.load()
    assert reg.version and reg.version != "unknown"
    all_pfam = {p for e in reg.toxin_functions for p in e.get("pfam", [])}
    # verified-correct accessions must remain in the registry
    for acc in ("PF00161", "PF01742", "PF03497", "PF03495", "PF20835", "PF01123", "PF02950", "PF01375"):
        assert acc in all_pfam, f"{acc} missing from registry"


# --- v7.1.2 CRITICAL FIXES: viral tropism + oncogenic functions ----------------------

def test_furin_cleavage_enhancement_caught():
    """v7.1.2 CRITICAL: Guardian must catch furin-cleavage enhancement (viral tropism GOF)."""
    design = {"cargo_function": "enhanced furin cleavage site insertion to increase viral receptor binding and tropism"}
    v = safety_gate(design, actor="test")
    assert v.decision in ("refuse", "escalate"), f"furin cleavage slipped through as {v.decision}"
    assert any("furin" in h.detail.lower() or "tropism" in h.detail.lower() for h in v.hits), \
        "no furin/tropism hit found"


def test_dominant_negative_tp53_caught():
    """v7.1.2 CRITICAL: Guardian must catch dominant-negative TP53 (oncogenic GOF)."""
    design = {"cargo_function": "dominant-negative TP53 suppressor to ablate apoptosis checkpoints and enable unrestricted proliferation"}
    v = safety_gate(design, actor="test")
    assert v.decision in ("refuse", "escalate"), f"TP53 suppressor slipped through as {v.decision}"
    assert any("tumor" in h.detail.lower() or "tp53" in h.detail.lower() or "apoptosis" in h.detail.lower() for h in v.hits), \
        "no tumor-suppressor hit found"


# --- audit trail -----------------------------------------------------------------------

def test_audit_chain_tamper_evident():
    import os
    from pathlib import Path
    safety_gate({"cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}, actor="a")
    safety_gate({"goal": "benign FIX"}, actor="b")
    assert verify_chain()["ok"] is True
    # tamper: rewrite a recorded decision; the hash chain must break
    p = Path(os.environ["PEN_STACK_SAFETY_AUDIT"])
    lines = p.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["decision"] = "clear"
    lines[0] = json.dumps(rec, sort_keys=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert verify_chain()["ok"] is False


# --- verify() integration --------------------------------------------------------------

def test_verify_short_circuits_refused_design_and_attaches_safety():
    from pen_stack.verify import verify
    v = verify({"write_type": "insertion", "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]})
    assert v.safety is not None and v.safety.decision == "refuse"
    assert v.legal is None # not evaluated further
    assert v.confidence is None and v.rule_results == []
    assert v.no_fabrication is True
    assert any(f.get("kind") == "safety_refused" for f in v.scope_flags)


def test_verify_benign_design_carries_clear_safety():
    from pen_stack.verify import verify
    v = verify({"write_type": "insertion", "chrom": "chr19", "cargo_function": "human coagulation factor IX",
                "delivery_vehicle": "AAV"})
    assert v.safety is not None and v.safety.decision == "clear"
