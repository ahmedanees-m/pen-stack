"""Hazard registry, the curated, version-pinned signature source for the Guardian (v5.7, WS-SCREEN).

A *defensive* biosecurity screen. The registry holds, at the FUNCTION / FAMILY / TAXON level only (public
Pfam accessions + public control-list references), the controlled-hazard categories a genome-writing design
is screened against. It deliberately contains no hazard sequences and no operational/synthesis detail, it
is a safeguard, not a guarantee, and not a substitute for institutional biosafety review.

The matcher is intentionally EXPLICIT (keyword/Pfam/alias tokens from the curated config), not a heuristic:
a safety control should be auditable. Flags come ONLY from the registry (or, when enabled, a wrapped external
screener), never fabricated. The function screen is what catches an AI-designed homolog: a low-identity
sequence still carries a hazardous FUNCTION annotation, and function, not homology, is the load-bearing axis.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml

from pen_stack._resources import resource
from pen_stack.safety.screen import ScreenHit

_REGISTRY_REL = "configs/safety/hazard_registry.yaml"


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _sep_norm(s: Any) -> str:
    """Lowercase and collapse separator runs (whitespace / hyphen / underscore) to a single space, so
    "furin-cleavage", "furin_cleavage" and "furin cleavage" are one token. Keeps the matcher robust to the
    hyphen/space/underscore variation that is ubiquitous in free-text function descriptions."""
    return re.sub(r"[\s_\-]+", " ", _norm(s)).strip()


def _kw_match(kw: str, text: str) -> bool:
    """Separator-insensitive, word-boundary keyword match (v7.1.2). Two failure modes of a plain substring test:
    (1) over-broad - the short ricin keyword "rip" matches inside "transc-RIP-tion", a word in almost every
    genome-editing design, so a benign promoter cassette would false-refuse as ricin; (2) too-narrow - a
    hyphenated "furin-cleavage" would slip past the space-form keyword "furin cleavage". Normalising separators
    then matching on alphanumeric boundaries fixes both: "rip" matches "RIP" standalone but not inside a longer
    word, and "furin cleavage" / "furin-cleavage" / "furin_cleavage" all match."""
    k = _sep_norm(kw)
    if not k:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", _sep_norm(text)) is not None


def _design_function_tokens(design: dict) -> set[str]:
    """Normalised function annotations declared on a design (NOT free-text justification)."""
    toks: set[str] = set()
    for k in ("cargo_function", "function_annotation", "goal_function"):
        v = design.get(k)
        if v:
            toks.add(_norm(v))
    for k in ("function_tags", "pfam_domains", "annotations"):
        for v in design.get(k) or []:
            toks.add(_norm(v))
    return {t for t in toks if t}


def _design_pfam(design: dict) -> set[str]:
    return {_norm(p) for p in (design.get("pfam_domains") or []) if p}


def _design_taxon_text(design: dict) -> str:
    return " ".join(_norm(design.get(k)) for k in ("source_taxon", "organism", "host_taxon") if design.get(k))


@dataclass
class HazardRegistry:
    """Loaded, version-pinned hazard signatures + the screen methods that consume them."""

    version: str
    toxin_functions: list[dict] = field(default_factory=list)
    regulated_taxa: list[dict] = field(default_factory=list)
    controlled_functions: list[dict] = field(default_factory=list)
    chimera_rules: list[dict] = field(default_factory=list)
    oncogenic_manipulation: dict = field(default_factory=dict)
    external_enabled: bool = False
    external_hook: Callable[[str], list[ScreenHit]] | None = None

    # ---- loading -----------------------------------------------------------
    @classmethod
    def load(cls, path: str | None = None, *, external_hook: Callable[[str], list[ScreenHit]] | None = None
             ) -> "HazardRegistry":
        raw = yaml.safe_load(resource(path or _REGISTRY_REL).read_text(encoding="utf-8"))
        return cls(
            version=raw.get("registry_version", "unknown"),
            toxin_functions=raw.get("toxin_functions", []),
            regulated_taxa=raw.get("regulated_taxa", []),
            controlled_functions=raw.get("controlled_functions", []),
            chimera_rules=raw.get("chimera_rules", []),
            oncogenic_manipulation=raw.get("oncogenic_manipulation", {}),
            external_enabled=external_hook is not None,
            external_hook=external_hook,
        )

    def _prov(self, entry: dict) -> dict:
        return {"registry_version": self.version, "signature_id": entry.get("id"),
                "control_ref": entry.get("control_ref"), "source": "hazard_registry (function/family-level)"}

    # ---- screens (each returns typed, provenanced hits) --------------------
    def function_flags(self, design: dict) -> list[ScreenHit]:
        """Toxin / controlled-FUNCTION screen. Matches declared Pfam domains OR function keywords.
        Catches AI-homologs: a low-identity sequence with a hazardous function annotation still flags."""
        hits: list[ScreenHit] = []
        toks = _design_function_tokens(design)
        pfam = _design_pfam(design)
        for entry in self.toxin_functions + self.controlled_functions:
            by_pfam = pfam & {_norm(p) for p in entry.get("pfam", [])}
            by_kw = {kw for kw in (entry.get("keywords") or []) if any(_kw_match(kw, t) for t in toks)}
            if by_pfam or by_kw:
                ev = {}
                if by_pfam:
                    ev["matched_pfam"] = sorted(by_pfam)
                if by_kw:
                    ev["matched_keywords"] = sorted(by_kw)
                hits.append(ScreenHit(kind="function_flag", detail=entry["name"],
                                      severity=entry.get("severity", "medium"),
                                      provenance=self._prov(entry), evidence=ev))
        return hits

    def oncogenic_flags(self, design: dict) -> list[ScreenHit]:
        """Oncogenic-manipulation PATTERN screen (v7.1.2). Flags the COMBINATION that a flat keyword list misses:
        a tumor-suppressor gene with a disruptive verb, an oncogene with an activating signature, or an
        immortalization signature. The asymmetry spares therapy without an allow-list (restoring a suppressor /
        silencing an oncogene matches neither). Escalates to human review (dual-use, legitimate cancer-model path)."""
        cfg = self.oncogenic_manipulation
        if not cfg:
            return []
        # screen the declared function annotations only (the artifact, not any free-text justification)
        text = " " + " | ".join(sorted(_design_function_tokens(design))) + " "
        if not text.strip(" |"):
            return []

        def has(keys: list[str]) -> list[str]:
            return [k for k in (keys or []) if _norm(k) in text]

        supp = has(cfg.get("tumor_suppressors"))
        onco = has(cfg.get("oncogenes"))
        disrupt = has(cfg.get("disrupt_verbs"))
        activate = has(cfg.get("activate_signatures"))
        immortal = has(cfg.get("immortalization"))
        therapy = has(cfg.get("therapy_context"))

        reasons = []
        if supp and disrupt:
            reasons.append(f"tumor-suppressor disruption ({supp[0]} + {disrupt[0]})")
        if onco and activate:
            reasons.append(f"oncogene activation ({onco[0]} + {activate[0]})")
        if immortal:
            reasons.append(f"immortalization signature ({immortal[0]})")
        if not reasons:
            return []
        # therapeutic restoration / supplementation with NO disruptive/activating/immortalization signal -> clear.
        if therapy and not (disrupt or activate or immortal):
            return []
        return [ScreenHit(kind="oncogenic_flag", detail=cfg.get("name", "oncogenic manipulation"),
                          severity=cfg.get("severity", "medium"), provenance=self._prov(cfg),
                          evidence={"patterns": reasons,
                                    "suppressor": supp[:2], "oncogene": onco[:2], "disrupt": disrupt[:2],
                                    "activate": activate[:2], "immortalization": immortal[:2]})]

    def taxon_flags(self, design: dict) -> list[ScreenHit]:
        """Regulated-pathogen-TAXON screen (Select Agent / Australia Group membership by declared source)."""
        hits: list[ScreenHit] = []
        text = _design_taxon_text(design)
        if not text:
            return hits
        for entry in self.regulated_taxa:
            aliases = [_norm(a) for a in ([entry.get("name")] + (entry.get("aliases") or [])) if a]
            matched = [a for a in aliases if a and a in text]
            if matched:
                hits.append(ScreenHit(kind="taxon_flag", detail=entry["name"],
                                      severity=entry.get("severity", "medium"),
                                      provenance=self._prov(entry), evidence={"matched_alias": matched[0]}))
        return hits

    def chimera_context(self, design: dict) -> list[ScreenHit]:
        """Hazardous ASSEMBLY of individually-benign parts (toxin+broad delivery; virulence+replication;
        split-hazard across sub-designs). Operates on declared structure, never invents a part."""
        hits: list[ScreenHit] = []
        rules = {r["id"]: r for r in self.chimera_rules}

        cf = _norm(design.get("cargo_function"))
        has_toxin = bool(self.function_flags(design)) or bool(cf) and any(
            _kw_match(kw, cf) for e in self.toxin_functions for kw in (e.get("keywords") or []))
        broad = _norm(design.get("delivery_tropism")) in {"broad", "broad_systemic", "systemic"} or \
            _norm(design.get("delivery_vehicle")) in {"aav9", "aavrh10"}
        replicating = bool(design.get("replication_competent"))
        patho = any(_norm(kw) in _design_function_tokens(design)
                    for e in self.controlled_functions if e["id"] == "FUNC-PATHO-ESSENTIAL"
                    for kw in (e.get("keywords") or [])) or "pathogen_essential" in _design_function_tokens(design)

        if has_toxin and broad and "CHIM-TOXIN-PAYLOAD" in rules:
            r = rules["CHIM-TOXIN-PAYLOAD"]
            hits.append(ScreenHit(kind="chimera_context", detail=r["detail"], severity=r["severity"],
                                  provenance=self._prov(r), evidence={"toxin_payload": True, "broad_delivery": True}))
        if (patho or replicating and self.taxon_flags(design)) and replicating and "CHIM-PATHO-REPLICATION" in rules:
            r = rules["CHIM-PATHO-REPLICATION"]
            hits.append(ScreenHit(kind="chimera_context", detail=r["detail"], severity=r["severity"],
                                  provenance=self._prov(r), evidence={"virulence_or_taxon": True, "replication_competent": True}))

        # split-hazard: scan sub-designs / multi-edit plan; if the assembled plan carries a hazardous
        # function/taxon that no single sub-design fully declares, flag the assembly. Type-guarded so an
        # unexpected field shape can never crash the gate (the safety gate must never break verify()).
        subs: list[dict] = []
        for key in ("sub_designs", "multiplex", "edits"):
            v = design.get(key)
            if isinstance(v, list):
                subs += [s for s in v if isinstance(s, dict)]
        if subs and "CHIM-SPLIT-HAZARD" in rules:
            sub_hits = [h for s in subs for h in (self.function_flags(s) + self.taxon_flags(s))]
            if sub_hits or self.taxon_flags(design) or patho:
                r = rules["CHIM-SPLIT-HAZARD"]
                worst = "high" if any(h.severity == "high" for h in sub_hits) or \
                    any(h.severity == "high" for h in self.taxon_flags(design)) else r["severity"]
                hits.append(ScreenHit(kind="chimera_context", detail=r["detail"], severity=worst,
                                      provenance=self._prov(r),
                                      evidence={"n_sub_designs": len(subs), "split_hazard": True}))
        return hits

    def sequence_homology(self, seq: str | None) -> list[ScreenHit]:
        """Baseline sequence-homology screen. The transparent baseline does NOT embed hazard sequences;
        real homology screening is delegated to a wrapped external screener (IBBIS Common Mechanism /
        SecureDNA-style) via `external_screen`. Returns [] here (a safeguard, not a guarantee)."""
        if self.external_enabled and seq:
            return self.external_screen(seq)
        return []

    def external_screen(self, seq: str | None) -> list[ScreenHit]:
        """Wrapped external sequence screener (disabled unless an `external_hook` was supplied at load)."""
        if not (self.external_enabled and self.external_hook and seq):
            return []
        return list(self.external_hook(seq))
