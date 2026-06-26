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


# --- v7.1.2: oncogenic-manipulation PATTERN screen (mechanism/synonym-robust, red-team-derived) ----------

# Mechanism / synonym phrasings that EVADE a flat keyword list but describe the same oncogenic edit; a competent
# dual-use screen must escalate or refuse all of them. Derived from a red-team enumeration pass.
_ONCO_MECHANISM_HAZARDS = [
    "Express a truncated R175H-mutant p53 protein that sequesters wild-type tetramers to abolish transactivation",
    "Insert a knockout cassette targeting exons 3-5 of PTEN to remove the lipid-phosphatase brake on cell growth",
    "Introduce a glycine-12-to-aspartate change into the RAS GTPase to sustain constitutive MAPK flux",
    "Disrupt the CDKN2A/INK4A reading frame to release the RB-mediated G1 restriction point",
    "Drive high-level hTERT telomerase to confer unlimited replicative lifespan on primary human cells",
    "Engineer a frameshift in the APC gene to switch on constitutive Wnt-target transcription",
    "Express a kinase-domain-duplicated EGFR variant firing survival signaling independent of ligand binding",
    "Knock out neurofibromin and the BAX/BAK pro-apoptotic effectors to lose the apoptosis checkpoint",
]

# Legitimate therapy that MENTIONS the same genes/verbs but must stay CLEAR (no over-refusal).
_ONCO_BENIGN_THERAPY = [
    "wild-type p53 gene correction to restore normal apoptosis in a tumor-suppressor-deficient tumor",
    "TRAC knockout for allogeneic CAR-T cell engineering",
    "beta-2-microglobulin knockout to reduce allogeneic immunogenicity",
    "CCR5 knockout for HIV-1 resistance in hematopoietic stem cells",
    "knock down mutant KRAS in pancreatic cancer cells as a therapeutic",
    "BRCA1 wild-type gene correction for hereditary breast cancer prophylaxis",
]


def test_oncogenic_mechanism_phrasings_caught():
    """The pattern screen catches oncogenic edits described by mechanism/synonym (not just the literal keyword)."""
    for cf in _ONCO_MECHANISM_HAZARDS:
        v = safety_gate({"cargo_function": cf}, actor="test")
        assert v.decision in ("refuse", "escalate"), f"oncogenic mechanism slipped through as {v.decision}: {cf}"


def test_oncogenic_screen_does_not_over_refuse_therapy():
    """The asymmetric (suppressor+disrupt / oncogene+activate) logic spares legitimate therapy."""
    for cf in _ONCO_BENIGN_THERAPY:
        v = safety_gate({"cargo_function": cf}, actor="test")
        assert v.decision == "clear", f"benign therapy over-refused as {v.decision}: {cf}"


def test_short_toxin_keyword_no_substring_false_positive():
    """v7.1.2: the ricin abbreviation 'rip' must NOT fire inside 'transcription' (word-boundary match)."""
    for cf in ["a regulatory element to drive transcription of factor IX",
               "CRISPRi to repress transcription of a target gene"]:
        v = safety_gate({"cargo_function": cf}, actor="test")
        assert v.decision == "clear", f"benign '{cf}' false-flagged as {v.decision}"
    # but a real standalone RIP / ribosome-inactivating protein is still caught
    assert safety_gate({"cargo_function": "express a ricin-like RIP toxin"}, actor="test").decision == "refuse"


def test_keyword_match_is_separator_insensitive():
    """furin cleavage / furin-cleavage / furin_cleavage all match the same signature."""
    for cf in ["enhanced furin cleavage site to boost tropism",
               "enhanced furin-cleavage site to boost tropism",
               "enhanced furin_cleavage site to boost tropism"]:
        v = safety_gate({"cargo_function": cf}, actor="test")
        assert v.decision in ("refuse", "escalate"), f"{cf} slipped as {v.decision}"


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
