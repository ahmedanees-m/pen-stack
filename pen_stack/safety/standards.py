"""Alignment of the Guardian biosecurity screen to community synthesis-screening standards (v6.12 PEN-VERIFY, F-WS3).

The Guardian is an IN-DESIGN, function/family/taxon-level screen. The community synthesis-screening standards
(the IBBIS Common Mechanism, SecureDNA) screen synthesis orders at the sequence level. This module maps the
Guardian's four screen kinds and its four decisions onto the Common Mechanism's reported categories and
ScreenStatus values, and reports the concordance on a labelled set, so the two interoperate. It is a
concordance, not a certification: the full sequence-screening pipeline is BioFirewall (Stage K), and the
authoritative screen is the standard's own tool. The mapping never changes a Guardian decision; it only
expresses it in the standard's vocabulary.

References (verified):
  IBBIS Common Mechanism for DNA Synthesis Screening (CLI: commec), IBBIS, MIT-licensed,
    https://github.com/ibbis-bio/common-mechanism ; Wheeler et al. 2024, Applied Biosafety 29(2):71-78,
    DOI 10.1089/apb.2023.0034.
  SecureDNA, SecureDNA Foundation, privacy-preserving cryptographic screening; Baum et al.,
    arXiv:2403.14023 (DOI 10.48550/arXiv.2403.14023).
  US Federal Select Agents Program: 42 CFR 73, 7 CFR 331, 9 CFR 121 (selectagents.gov).
  Australia Group control lists for human/animal pathogens and toxins and for plant pathogens
    (australiagroup.net).
"""
from __future__ import annotations

from typing import Any

from pen_stack.safety.policy import SafetyVerdict, decide
from pen_stack.safety.screen import screen_design

COMMON_MECHANISM = {
    "name": "The Common Mechanism for DNA Synthesis Screening (commec)",
    "run_by": "IBBIS (International Biosecurity and Biosafety Initiative for Science)",
    "license": "MIT",
    "repo": "https://github.com/ibbis-bio/common-mechanism",
    "citation_doi": "10.1089/apb.2023.0034",
    # ScreenStatus values reported by the Common Mechanism (commec/config/result.py).
    "screen_status": ["Pass", "Warning", "Flag", "Warning (Cleared)", "Flag (Cleared)"],
    "screen_steps": ["Biorisk Search", "Nucleotide Taxonomy Search", "Protein Taxonomy Search",
                     "Low Concern Search"],
    # the three user-facing output categories (IBBIS FAQ).
    "categories": [
        "flagged sequences of concern (virulence factors and toxins)",
        "areas of similarity to regulated pathogens",
        "matches to genes with a known benign function",
    ],
}

SECUREDNA = {
    "name": "SecureDNA",
    "run_by": "SecureDNA Foundation",
    "mechanism": "privacy-preserving cryptographic exact-match window screening (>= 30 nt)",
    "citation_arxiv": "2403.14023",
    "output": "binary match to deny (exemption-token override); no public per-category taxonomy, so the "
              "Guardian aligns to it only at the pass/deny level.",
}

CONTROL_LISTS = {
    "us_select_agents": {"refs": ["42 CFR 73", "7 CFR 331", "9 CFR 121"], "url": "https://www.selectagents.gov/"},
    "australia_group": {
        "lists": ["List of Human and Animal Pathogens and Toxins for Export Control",
                  "List of Plant Pathogens for Export Control"],
        "url": "https://www.australiagroup.net/",
    },
}

# Guardian screen kind -> Common Mechanism step + reported category.
SCREEN_KIND_TO_CM = {
    "function_flag": {"cm_step": "Biorisk Search",
                      "cm_category": "flagged sequences of concern (virulence factors and toxins)"},
    "taxon_flag": {"cm_step": "Nucleotide/Protein Taxonomy Search",
                   "cm_category": "areas of similarity to regulated pathogens"},
    "sequence_homology": {"cm_step": "Biorisk/Taxonomy homology",
                          "cm_category": "homology to a regulated toxin, virus or non-viral pathogen"},
    # the Common Mechanism screens per-window sequences, not declared assemblies; chimera-context has no direct
    # CM step and is reported honestly as an in-design signal the per-window standard does not cover.
    "chimera_context": {"cm_step": "(none: assembly-level, not per-window)",
                        "cm_category": "assembly-level hazard not screened by the per-window standard"},
}

# Guardian decision -> Common Mechanism ScreenStatus (escalate maps to Warning, the CM "equally-good matches"
# ambiguous tie; refuse maps to Flag, the CM higher-concern hit).
DECISION_TO_CM_STATUS = {"clear": "Pass", "flag": "Warning", "escalate": "Warning", "refuse": "Flag"}
# Guardian decision -> SecureDNA order-level outcome (binary, with review for the ambiguous middle).
DECISION_TO_SECUREDNA = {"clear": "pass", "flag": "review", "escalate": "review", "refuse": "deny"}


def align_to_common_mechanism(safety: SafetyVerdict) -> dict[str, Any]:
    """Express a Guardian SafetyVerdict in the standards' vocabulary: the order-level Common Mechanism
    ScreenStatus, the SecureDNA pass/deny outcome, and the per-hit category mapping. No decision is changed."""
    hits = [{"guardian_kind": h.kind, "detail": h.detail, "severity": h.severity,
             **SCREEN_KIND_TO_CM.get(h.kind, {"cm_step": "(unmapped)", "cm_category": "(unmapped)"})}
            for h in (safety.hits or [])]
    return {
        "guardian_decision": safety.decision,
        "common_mechanism_status": DECISION_TO_CM_STATUS.get(safety.decision, "Warning"),
        "securedna_outcome": DECISION_TO_SECUREDNA.get(safety.decision, "review"),
        "hits": hits,
        "note": "in-design concordance, not certification; BioFirewall (Stage K) is the downstream "
                "sequence-screening gate, and the standard's own tool is authoritative.",
    }


def _decision_for(design: dict) -> SafetyVerdict:
    """Screen a design and decide, without the audit side-effect of the full gate (this is a report path)."""
    hits = screen_design(design)
    decision, reason = decide(hits)
    return SafetyVerdict(decision=decision, hits=hits, reason=reason,
                         provenance={"source": "standards.concordance"})


def concordance_report(probes: list[dict] | None = None) -> dict[str, Any]:
    """Run the Guardian over a labelled set and report, verbatim, the concordance between its decisions
    (expressed as Common Mechanism ScreenStatus) and the expected status (Pass for benign, Flag/Warning for a
    hazard). Loads the committed safety probes when none are supplied."""
    if probes is None:
        import yaml

        from pen_stack._resources import resource
        raw = yaml.safe_load(resource("configs/safety/probes.yaml").read_text(encoding="utf-8"))
        probes = [{"name": e.get("name"), "design": e["design"], "label": "benign"}
                  for e in raw.get("benign_controls", [])]
        probes += [{"name": e.get("name"), "design": e["design"], "label": "hazard"}
                   for e in raw.get("hazard_probes", [])]
    rows = []
    for p in probes:
        sv = _decision_for(p["design"])
        cm = DECISION_TO_CM_STATUS.get(sv.decision, "Warning")
        # benign should map to Pass; a hazard should map to a non-Pass status (Warning/Flag).
        expected_nonpass = p["label"] == "hazard"
        concordant = (cm != "Pass") == expected_nonpass
        rows.append({"name": p["name"], "label": p["label"], "guardian_decision": sv.decision,
                     "common_mechanism_status": cm, "concordant": concordant})
    n = len(rows)
    n_conc = sum(r["concordant"] for r in rows)
    return {
        "n": n, "n_concordant": n_conc, "concordance": round(n_conc / n, 4) if n else None,
        "discordances": [r for r in rows if not r["concordant"]],
        "rows": rows,
        "standard": COMMON_MECHANISM["name"], "standard_doi": COMMON_MECHANISM["citation_doi"],
        "note": "Reported verbatim. A concordance between the in-design Guardian and the Common Mechanism's "
                "reported status, not a certification; the standard's own tool remains authoritative and "
                "BioFirewall (Stage K) is the downstream sequence-screening gate.",
    }
