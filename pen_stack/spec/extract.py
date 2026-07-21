"""Grounded prose-to-WriteSpec extractor.

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

# Matches the symbol shape the gene resolver itself accepts. A shorter bound here than in the resolver would make
# a symbol's fate depend on its length: an 8-character symbol reaches the resolver while a 9-character one is never
# offered to it, so real long symbols (ARHGEF10L, TNFRSF13B) would go unseen.
_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})\b")
_WRITE_TYPE_KW = [
    # Multiplex leads: a request that names the modality outright ("multiplex knockout of TRAC and B2M") also
    # carries the verb of the edit it multiplexes, and reading the verb first would report a single-locus write
    # for a request that said the opposite.
    ("multiplex", ["multiplex", "multiple loci", "simultaneously edit"]),
    ("excision", ["excise", "delete", "knock out", "knockout", "remove ", "disrupt"]),
    ("inversion", ["invert", "inversion", "flip "]),
    ("replacement", ["replace", "correct the", "correct a", "swap", "base edit", "prime edit", "repair the"]),
    ("regulatory_rewrite", ["regulatory", "promoter swap", "rewrite the promoter", "tune expression", "upregulate", "knock down"]),
    ("landing_pad_install", ["landing pad", "landing-pad", "install an att", "install a landing", "attp", "bxb1 site"]),
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
    """Gene-symbol tokens: what the request could be naming as an edit site.

    A token is excluded when it is jargon, when it resolves as a cell line or type (HEK293T), or when it lies
    within a term the prose has already used for something else. The CD8 of 'CD8 T cells' names the population and
    a site preposition in front of it ('... in CD8 T cells') would otherwise anchor it as the target; a vehicle
    written in capitals ('deliver with LENTIVIRUS') has the shape of a symbol and would otherwise be read as one.
    """
    from pen_stack.spec.resolvers.cell import _CELLS
    from pen_stack.spec.resolvers.gene import _STOP
    cell_keys = {k.upper() for k in _CELLS}
    taken = [(s, e) for s, e, _ in _cell_mentions(prose)] + [(s, e) for s, e, _ in _vehicle_mentions(prose.lower())]
    return [m.group(1) for m in _GENE_RE.finditer(prose)
            if m.group(1) not in _STOP and m.group(1).upper() not in cell_keys
            and not any(s < m.end() and m.start() < e for s, e in taken)]


# The EDIT SITE is signalled by a site preposition ("into/at/in/within X") or a suffix ("X locus/site"); the
# CARGO is what is written ("insert X …"). Preferring a site-anchored token stops a gene-like cargo name from
# hijacking the target (e.g. "insert a CD19 CAR into TRAC" -> target is TRAC, not CD19).
_SITE_PREP = re.compile(r"\b(?:into|at|in|to|within|inside)\s+(?:the\s+)?([A-Z][A-Z0-9]{1,9})\b")
_SITE_SUFFIX = re.compile(r"\b([A-Z][A-Z0-9]{1,9})\b\s+(?:locus|loci|site|safe[- ]?harbou?r)\b")
# Genes conjoined to the target in one request: "TRAC and B2M", "TRAC, B2M and CIITA".
_CONJ = re.compile(r"\s*(?:,\s*and|,|and|&|/|\+)\s+([A-Z][A-Z0-9]{1,9})\b")

# A delivery vehicle matches as a whole word whose parts all belong to the vehicle: the recombinant /
# self-complementary prefixes (rAAV, scAAV), the serotype suffixes (AAV9, AAVrh74, AAV-DJ, AAV-PHP.eB) and a
# plural (AAVs). A locus whose name merely begins with the same letters - AAVS1, the standard safe harbour - is
# excluded by the SUFFIX boundary, since "S1" is not a serotype; the prefixes therefore cannot re-admit it.
_AAV = r"(?:scr|sc|ss|r)?aav(?:\d+|rh\d+|-?dj|-?php[\w.]*)?s?"
_VEH = [(rf"dual[\s-]*{_AAV}", "AAV_dual"),
        (_AAV, "AAV_single"), (r"adeno[\s-]*associated\s*virus(?:es)?", "AAV_single"),
        (r"lentivir\w*", "lentivirus"), (r"lnps?", "LNP"), (r"electroporat\w*", "electroporation"),
        (r"rnps?", "electroporation"), (r"adenovir\w*", "adenovirus")]
# A vehicle can be named in order to be RULED OUT. The cue sits next to the mention: before it for an exclusion
# ("instead of AAV", "not lentivirus"), after it for a capacity verdict ("AAV is too small").
#
# A cue only counts when it GOVERNS the mention, which needs two guards. It must stand in the same clause, since
# "this does not matter: use AAV9" negates the matter, not the AAV; and it must be adjacent, reaching the vehicle
# through nothing but a preposition or an article, since "not only AAV but also lentivirus" negates "only". A bare
# search of the preceding characters satisfies neither and rules out vehicles the request chose.
_CLAUSE_SPLIT = re.compile(r"[;:,.]|\bso\b|\bbut\b|\bthen\b")
_VEH_REJECT_BEFORE_RE = re.compile(
    r"\b(?:instead\s+of|rather\s+than|other\s+than|without|avoid(?:ing)?|rules?\s+out|ruled\s+out|ruling\s+out|"
    r"cannot\s+use|can(?:'|no)?t\s+use|not)\s+"
    r"(?:(?:using|use|with|via|by|deliver(?:ed|ing)?|packag(?:e|ed|ing)|into|a|an|the)\s+){0,2}$")
_VEH_REJECT_AFTER = ("too small", "too large", "too big", "won't fit", "will not fit", "does not fit",
                     "doesn't fit", "cannot carry", "can't carry", "exceeds", "is insufficient")
# Electroporation carries no cargo of its own, so it imposes no packaging capacity and does not compete with the
# vector that does. Naming both is the standard ex vivo knock-in ("Cas9 RNP by electroporation with an AAV6
# donor"), where the constraint that matters belongs to the donor capsid, not to the pulse.
_NON_PACKAGING = {"electroporation"}


def _longest_non_overlapping(hits: list[tuple[int, int, object]]) -> list[tuple[int, int, object]]:
    """Keep the longest term starting earliest and drop anything its span touches, so one term is never read as
    two. Terms in these tables nest ('293t' inside 'hek293t', 't cell' inside 'cd8 t cell', the AAV inside 'dual
    AAV') and also OVERLAP without nesting: in 'HEK293T cells' the line's trailing t is the t of 't cell', and in
    'Jurkat cells' likewise, so a containment test alone would read one cell line as two different cell types."""
    kept: list[tuple[int, int, object]] = []
    for h in sorted(hits, key=lambda x: (x[0], -(x[1] - x[0]))):
        if not any(h[0] < k[1] and k[0] < h[1] for k in kept):
            kept.append(h)
    return kept


def _vehicle_mentions(low: str) -> list[tuple[int, int, str]]:
    """Every delivery vehicle named in the prose, with its span, in prose order."""
    hits = [(m.start(), m.end(), veh) for pat, veh in _VEH
            for m in re.finditer(rf"(?<![a-z0-9]){pat}(?![a-z0-9])", low)]
    return sorted(_longest_non_overlapping(hits))


def _vehicle_is_ruled_out(low: str, start: int, end: int) -> bool:
    """True when the text next to a vehicle mention rules it out rather than choosing it.

    Both sides read only within the mention's own clause, and the exclusion cue must reach the vehicle directly."""
    before = _CLAUSE_SPLIT.split(low[max(0, start - 48):start])[-1]
    if _VEH_REJECT_BEFORE_RE.search(before):
        return True
    after = _CLAUSE_SPLIT.split(low[end:end + 30])[0]
    return any(c in after for c in _VEH_REJECT_AFTER)


def _cell_mentions(prose: str) -> list[tuple[int, int, str]]:
    """Every cell term named, with its span, in prose order."""
    from pen_stack.spec.resolvers.cell import _CELLS
    low = prose.lower()
    hits: list[tuple[int, int, str]] = []
    for phrase in _CELLS:
        i = low.find(phrase)
        while i != -1:
            hits.append((i, i + len(phrase), phrase))
            i = low.find(phrase, i + 1)
    return sorted(_longest_non_overlapping(hits))


def _pick_target_token(prose: str, gene_toks: list[str]) -> str | None:
    """Choose the token naming the edit SITE. Prefer a site-anchored token ('into/at X', 'X locus'); otherwise
    fall back to the first gene token (a bare target like 'knock out PCSK9'). gene_toks is already stop/cell-filtered."""
    if not gene_toks:
        return None
    valid = set(gene_toks)
    anchored = [(m.start(1), m.group(1)) for m in _SITE_PREP.finditer(prose) if m.group(1) in valid]
    anchored += [(m.start(1), m.group(1)) for m in _SITE_SUFFIX.finditer(prose) if m.group(1) in valid]
    if anchored:
        anchored.sort()
        return anchored[0][1]
    return gene_toks[0]


def _conjoined_tokens(prose: str, tgt_tok: str, valid: set[str]) -> list[str]:
    """Gene tokens chained to the target by a conjunction ('TRAC and B2M', 'TRAC, B2M and CIITA').

    Only a token joined directly to the target counts, so a gene-like CARGO name elsewhere in the prose
    ('insert a CD19 CAR into TRAC') is not mistaken for a second target."""
    m = re.search(rf"\b{re.escape(tgt_tok)}\b", prose)
    if not m:
        return []
    out: list[str] = []
    tail = prose[m.end():]
    while (m2 := _CONJ.match(tail)) and m2.group(1) in valid and m2.group(1) not in out and m2.group(1) != tgt_tok:
        out.append(m2.group(1))
        tail = tail[m2.end():]
    return out


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
    tgt_tok = _pick_target_token(prose, gene_toks)
    if tgt_tok:
        g = resolve_gene(tgt_tok)
        if g.resolved:
            gene_resolved = g
        else:
            unresolved.append(tgt_tok)
    if gene_resolved is not None:
        loc = resolve_locus(tgt_tok)
        target = Target(kind="gene", gene=gene_resolved, locus=loc if loc.resolved else None)
        prov["target.gene"] = "explicit"
        # Genes conjoined to the target ("knock out TRAC and B2M") are further targets, not cargo: keeping only the
        # first would design against half the request. The primary stays in ``gene`` for every existing consumer.
        for tok in _conjoined_tokens(prose, tgt_tok, set(gene_toks)):
            g2 = resolve_gene(tok)
            if g2.resolved:
                target.additional_genes.append(g2)
            elif tok not in unresolved:
                unresolved.append(tok)
        if target.additional_genes:
            names = [gene_resolved.id or tgt_tok] + [g.id or "?" for g in target.additional_genes]
            prov["target.additional_genes"] = "explicit"
            assumptions.append(f"the request names {len(names)} target genes ({', '.join(names)}); "
                               f"{names[0]} is recorded as the primary target and the rest as additional targets")
            if wt != "multiplex":
                clarifications.append(f"The request names {len(names)} target genes ({', '.join(names)}) but reads "
                                      f"as a single {wt} write. Should every listed gene be edited?")
        # A symbol shaped like a gene but absent from the atlas is carried through unvalidated, by design, so that a
        # genuinely novel gene still works. Say so on the spec: without it, an unconfirmed symbol is indistinguishable
        # from a grounded one at a glance, and whether it is carried at all would rest on its length.
        if (gene_resolved.confidence or 0) < 0.5:
            assumptions.append(f"target symbol '{tgt_tok}' is not in the writable-genome atlas; it is carried "
                               f"unvalidated, with no coordinates resolved for it")
            clarifications.append(f"Target symbol '{tgt_tok}' could not be confirmed against the writable-genome "
                                  f"atlas. Is it the intended gene?")
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
    # A request may offer a choice ("in HeLa or Jurkat"). Resolving the terms in table order would commit the spec
    # to one of them and label it explicit, so distinct resolved cells are counted first and a choice is asked.
    cell = None
    named: list = []
    for _s, _e, phrase in _cell_mentions(prose):
        r = resolve_cell(phrase)
        if r is not None and r.resolved and r.id not in {x.id for x in named}:
            named.append(r)
    if len(named) > 1:
        clarifications.append(f"The request names more than one cell type "
                              f"({', '.join(c.label or c.text or str(c.id) for c in named)}). Which is the target?")
    elif len(named) == 1:
        cell = named[0]
        prov["cell_type"] = "explicit"
    else:
        ct = _detect_cell(prose)
        if ct is not None and ct.candidates:
            cell = ct
            prov["cell_type"] = "explicit"
            clarifications.append(f"Cell term '{ct.text}' is ambiguous: did you mean "
                                  f"{', '.join(c['label'] for c in ct.candidates)}?")
        else:
            clarifications.append("Which cell type or cell line is the target (e.g. HEK293T, primary T cells, "
                                  "HSPCs)?")

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
    # The named delivery vehicle, so the legality / capacity check can run. A request may mention several vehicles,
    # and may name one only to rule it out, so the vehicle is read from what the prose says ABOUT each mention
    # rather than from the order of the table: taking the first entry that matched anywhere would record the
    # vehicle the user rejected, and label it as though they had asked for it.
    mentions = _vehicle_mentions(low)
    chosen: list[str] = []
    for s, e, veh in mentions:
        if not _vehicle_is_ruled_out(low, s, e) and veh not in chosen:
            chosen.append(veh)
    if len(chosen) > 1 and len([v for v in chosen if v not in _NON_PACKAGING]) == 1:
        chosen = [v for v in chosen if v not in _NON_PACKAGING]  # the pulse and the capsid are not rivals
    if len(chosen) == 1:
        cons.delivery_limit = chosen[0]
        prov["constraints.delivery_limit"] = "explicit"
    elif len(chosen) > 1:  # two vehicles, no cue to separate them: ask rather than pick one and call it stated
        clarifications.append(f"The request names more than one delivery vehicle ({', '.join(chosen)}). "
                              f"Which should the design assume?")
    elif mentions:  # every vehicle named was ruled out, and none was put in its place
        clarifications.append("Every delivery vehicle named in the request is ruled out and no replacement is "
                              "named. Which vehicle should the design assume?")
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
