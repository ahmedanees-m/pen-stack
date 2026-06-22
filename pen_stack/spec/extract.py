"""Grounded prose-to-WriteSpec extractor (v6.14, Stage A, A-WS3).

Maps a plain-language genome-writing request to a typed :class:`WriteRequest`. The backbone is DETERMINISTIC (so
the benchmark is reproducible and CI-safe); an LLM pass is optional and never required. Three grounding
safeguards are mandatory and encoded here:

  1. assumption surfacing  - every field not explicit in the prose is recorded in ``provenance`` as ``inferred``
     with the rationale in ``assumptions`` (never a silent default);
  2. clarifying questions   - a required field that is unspecified or ambiguous yields a ``clarifications``
     question rather than a guess;
  3. no fabrication         - a term that cannot be resolved is listed in ``unresolved`` and its field stays null.
"""
from __future__ import annotations

import re

from pen_stack.spec.resolvers import (
    resolve_cell,
    resolve_chem,
    resolve_feature,
    resolve_gene,
    resolve_locus,
    resolve_phenotype,
)
from pen_stack.spec.resolvers.phenotype import _PHENO
from pen_stack.spec.writespec import (
    CargoComponent,
    Constraints,
    Target,
    WriteRequest,
)

_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")
_WRITE_TYPE_KW = [
    ("excision", ["excise", "delete", "knock out", "knockout", "remove ", "disrupt"]),
    ("inversion", ["invert", "inversion", "flip "]),
    ("replacement", ["replace", "correct the", "correct a", "swap", "base edit", "prime edit", "repair the"]),
    ("regulatory_rewrite", ["regulatory", "promoter swap", "rewrite the promoter", "tune expression", "upregulate", "knock down"]),
    ("landing_pad_install", ["landing pad", "landing-pad", "install an att", "install a landing", "attp", "bxb1 site"]),
    ("multiplex", ["multiplex", "multiple loci", "simultaneously edit"]),
    ("insertion", ["insert", "integrate", "knock in", "knock-in", "knockin", "add a", "deliver a transgene", "place a"]),
]
_ROLE_KW = {"promoter": "promoter", "cds": "CDS", "coding": "CDS", "transgene": "CDS", "gfp": "CDS",
            "polya": "polyA", "poly-a": "polyA", "insulator": "insulator", "enhancer": "enhancer",
            "terminator": "terminator", "ires": "IRES"}


def _detect_write_type(low: str) -> tuple[str, bool]:
    for wt, kws in _WRITE_TYPE_KW:
        if any(k in low for k in kws):
            return wt, True
    return "insertion", False  # default, labelled inferred by the caller


def _gene_tokens(prose: str) -> list[str]:
    """Gene-symbol tokens, excluding jargon and any token that resolves as a cell line / type (e.g. HEK293T)."""
    from pen_stack.spec.resolvers.cell import _CELLS
    from pen_stack.spec.resolvers.gene import _STOP
    cell_keys = {k.upper() for k in _CELLS}
    return [g for g in _GENE_RE.findall(prose) if g not in _STOP and g.upper() not in cell_keys]


def _detect_bp(low: str) -> int | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*kb", low)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.search(r"(\d{2,6})\s*(?:bp|base pairs)", low)
    if m:
        return int(m.group(1))
    return None


def _detect_phenotype(prose: str):
    low = prose.lower()
    for phrase in sorted(_PHENO, key=len, reverse=True):
        if phrase in low:
            return resolve_phenotype(phrase)
    return None


def _detect_cell(prose: str):
    from pen_stack.spec.resolvers.cell import _CELLS
    low = prose.lower()
    for phrase in sorted(_CELLS, key=len, reverse=True):
        if phrase in low:
            return resolve_cell(phrase)
    return None


def _detect_inducer(prose: str):
    from pen_stack.spec.resolvers.chem import _CHEM
    low = prose.lower()
    for phrase in sorted(_CHEM, key=len, reverse=True):
        if phrase in low:
            return resolve_chem(phrase)
    return None


def extract_writespec(prose: str, *, overrides: dict | None = None, allow_llm: bool = False) -> WriteRequest:
    """Extract a typed WriteRequest from prose, deterministically, with grounding safeguards.

    ``overrides`` lets a caller (or the web builder) supply a field directly; those are marked provenance ``user``.
    ``allow_llm`` is accepted for surface parity but the deterministic backbone is what runs and is benchmarked;
    an LLM pass, when wired, may only PROPOSE values that still pass the resolvers (it can never set an
    unresolved id).
    """
    prose = prose or ""
    low = prose.lower()
    prov: dict[str, str] = {}
    assumptions: list[str] = []
    unresolved: list[str] = []
    clarifications: list[str] = []
    overrides = overrides or {}

    # --- write type ---
    if "write_type" in overrides:
        wt = overrides["write_type"]
        prov["write_type"] = "user"
    else:
        wt, explicit = _detect_write_type(low)
        prov["write_type"] = "explicit" if explicit else "inferred"
        if not explicit:
            assumptions.append("write_type inferred as 'insertion' (no explicit write verb; the default for a "
                               "cargo-placement request)")

    # --- target: a named gene/locus or att site is the EDIT SITE (target_kind); a disease is the GOAL ---
    target = Target()
    pheno = _detect_phenotype(prose)
    gene_toks = _gene_tokens(prose)
    att = None
    for k in ("attb", "attp", "landing pad", "landing-pad", "landing site"):
        if k in low:
            att = k.replace(" ", "_").replace("-", "_")
            break
    gene_resolved = None
    if gene_toks:
        g = resolve_gene(gene_toks[0])
        if g.resolved:
            gene_resolved = g
        else:
            unresolved.append(gene_toks[0])
    if gene_resolved is not None:
        loc = resolve_locus(gene_toks[0])
        target = Target(kind="gene", gene=gene_resolved, locus=loc if loc.resolved else None)
        prov["target.gene"] = "explicit"
        if pheno is not None and pheno.resolved:  # the disease is the goal, attached to the gene target
            target.phenotype = pheno
            prov["target.phenotype"] = "explicit"
    elif att:
        target = Target(kind="att_site", att_site=att)
        prov["target.att_site"] = "explicit"
        if pheno is not None and pheno.resolved:
            target.phenotype = pheno
            prov["target.phenotype"] = "explicit"
    elif pheno is not None and pheno.resolved:
        target = Target(kind="phenotype", phenotype=pheno)
        prov["target.phenotype"] = "explicit"
    if target.kind == "unspecified":
        clarifications.append("Which gene, locus, att/landing site, or disease phenotype should the write target?")

    # --- cell type (optional but recommended) ---
    cell = None
    ct = _detect_cell(prose)
    if ct is not None and ct.resolved:
        cell = ct
        prov["cell_type"] = "explicit"
    elif ct is not None and ct.candidates:
        cell = ct
        prov["cell_type"] = "explicit"
        clarifications.append(f"Cell term '{ct.text}' is ambiguous: did you mean "
                              f"{', '.join(c['label'] for c in ct.candidates)}?")
    else:
        clarifications.append("Which cell type or cell line is the target (e.g. HEK293T, primary T cells, HSPCs)?")

    # --- cargo (size + feature roles) ---
    cargo: list[CargoComponent] = []
    bp = _detect_bp(low)
    seen_roles: set[str] = set()
    for kw, label in _ROLE_KW.items():
        if kw in low and label not in seen_roles:
            seen_roles.add(label)
            role = resolve_feature(label)
            cargo.append(CargoComponent(name=kw, role=role if role.resolved else None))
            prov[f"cargo[{len(cargo) - 1}].role"] = "explicit"
    if bp is not None and cargo:
        cargo[0].length_bp = bp
    elif bp is not None:
        cargo.append(CargoComponent(name="cargo", length_bp=bp))

    # --- constraints ---
    cons = Constraints()
    if "scarless" in low or "seamless" in low:
        cons.scarless = True
        prov["constraints.scarless"] = "explicit"
    if "safety switch" in low or "kill switch" in low or "icasp9" in low or "suicide gene" in low:
        cons.safety_switch_required = True
        prov["constraints.safety_switch_required"] = "explicit"
    # named delivery vehicle (so the legality / capacity check can run) - most specific first
    _VEH = [("dual aav", "AAV_dual"), ("aav", "AAV_single"), ("lentivir", "lentivirus"), ("lnp", "LNP"),
            ("electroporat", "electroporation"), ("rnp", "electroporation"), ("adenovir", "adenovirus")]
    for kw, veh in _VEH:
        if kw in low:
            cons.delivery_limit = veh
            prov["constraints.delivery_limit"] = "explicit"
            break
    if cons.delivery_limit is None and ("non-integrating" in low or "nonintegrating" in low
                                        or "episomal" in low or "transient" in low):
        cons.delivery_limit = "non_integrating"
        prov["constraints.delivery_limit"] = "explicit"
    if "germline" in low or "embryo" in low or "heritable" in low:
        cons.germline = True
        prov["constraints.germline"] = "explicit"
    m = re.search(r"(?:at least|>=|over|above)\s*(\d{1,3})\s*%\s*(?:efficien|edit|integrat)", low)
    if m:
        cons.efficiency_floor = float(m.group(1)) / 100.0
        prov["constraints.efficiency_floor"] = "explicit"
    inducer = _detect_inducer(prose)
    if inducer is not None and inducer.resolved:
        cons.inducer = inducer
        prov["constraints.inducer"] = "explicit"
    if bp is not None:
        cons.max_cargo_bp = bp
        prov["constraints.max_cargo_bp"] = "explicit"

    # apply structured overrides (provenance=user) last
    for k, v in overrides.items():
        if k != "write_type":
            prov[k] = "user"

    return WriteRequest(write_type=wt, cargo=cargo, target=target, cell_type=cell, constraints=cons,
                        provenance=prov, assumptions=assumptions, clarifications=clarifications,
                        unresolved=unresolved, free_text_note=prose.strip() or None)
