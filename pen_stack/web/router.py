"""Intent router for the hybrid co-scientist (v6.3). Deterministic (no LLM) so routing is reproducible.

Four lanes, each with its own provenance:
  * ``design``, a genome-writing request → RUN the engine (grounded numbers, guard ON).
  * ``explain``, a follow-up about a value already on the table ("what does that 0.55 mean") → metric guide +
                  the prior dossier (grounded interpretation).
  * ``meta``, a question about PEN-STACK itself ("how many enzymes? how is immunogenicity computed? how
                  accurate?") → the live capability facts (grounded).
  * ``general``, greetings + textbook biology ("hi", "what is AAV", "how does AAV work") → the LLM's trained
                  knowledge, EXPLICITLY labelled "general knowledge, not PEN-STACK-verified", with a pointer to
                  the engine wherever PEN-STACK could compute something concrete.

Bias: when a real design signal is present we route to ``design`` (the engine path is cheap and always grounds),
so a genuine request is never answered from ungrounded general knowledge.
"""
from __future__ import annotations

import re

_ACTION = re.compile(r"\b(insert|express|knock[\s-]?in|knock[\s-]?out|integrat|excis|deliver|edit|write|"
                     r"target|disrupt|correct|replace|place|add)\w*\b", re.I)
_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")
_VEHICLE = re.compile(r"\b(aav|lentivir|lenti|lnp|mrna|adenovir|hsv|electroporat|vector|capsid|vehicle)\w*\b", re.I)
# trailing \w* so inflected forms count as a signal too (sites, hepatocytes, HSPCs, iPSCs)
_LOCUS = re.compile(r"\b(locus|loci|site|safe[\s-]?harbour|safe[\s-]?harbor|aavs1|chr\d|enhancer|intron|exon)\w*\b", re.I)
_CELL = re.compile(r"\b(hepatocyt|liver|hspc|stem cell|ipsc|t[\s-]?cell|k562|hepg2|pbmc|cell line|cell type)\w*\b", re.I)
_CARGO = re.compile(r"\b(\d+(?:\.\d+)?\s*kb|\d{3,6}\s*bp|cargo|cassette|transgene|payload)\b", re.I)

_EXPLAIN = re.compile(r"\b(what (do|does|is) (that|these|those|this|the)\b|what do the\b|"
                      r"that (number|value|score)|those (numbers|values|scores)|the \d+(\.\d+)?\b|"
                      r"explain (that|this|the)|interpret|what does (it|that) mean|"
                      r"reference range|what range|is that (good|bad|high|low|safe)|how do i read)\b", re.I)

_META = re.compile(r"\b(pen[\s-]?stack|how (do|does) (you|pen)|how is .* (computed|calculated|derived|scored)|"
                   r"how many (?:[\w-]+\s+){0,2}(enzyme|writer|vector|vehicle|ax(?:e|is|es)|immune|metric|model|"
                   r"system|locus|loci|gene|cell|oracle)\w*|"
                   r"how accurate|accuracy|how reliable|validated|what (can|do) you (do|cover|offer|support)|"
                   r"your (coverage|capabilit|method|model|data|engine)|how (does|is) immunogenicity|"
                   r"what (model|oracle|data|dataset)s?\b|where do (the|these) (number|value)s? come from|"
                   r"how (do|does) (it|you|pen[\s-]?stack) (give|compute|calculate|get))\b", re.I)

_GREETING = re.compile(r"^\s*(hi|hii+|hey|hello|yo|hola|greetings|good (morning|afternoon|evening)|thanks?|"
                       r"thank you|ok(ay)?|cool|nice|great)\b", re.I)

# A back-reference follow-up to the previous answer ("and why?", "is that it?", "tell me more about that").
_FOLLOWUP = re.compile(r"^\s*(and |but |so |then |why|how come|really|are you sure|elaborate|tell me more|"
                       r"go on|more|continue|expand|what about)\b|"
                       r"\b(that|it|this|those|these|them|the (score|number|value|result|design|writer|site|plan))\b",
                       re.I)


def _prior_lane(history: list | None) -> str | None:
    """The lane of the most recent ASSISTANT turn (carried in memory), or None."""
    for turn in reversed(history or []):
        if turn.get("role") == "assistant" and turn.get("mode"):
            return str(turn.get("mode"))
    return None


def _looks_like_design(message: str) -> bool:
    """A real genome-writing request. CONSERVATIVE BY DESIGN (gate P-G2): a write/result request must never leak to
    the ungrounded general lane, so an explicit ACTION verb (insert/integrate/correct/knock-in/...) plus ANY ONE
    target signal (vehicle / locus / cell / cargo / a gene) routes to the grounded design lane. Without an action
    verb we still catch noun-phrase designs (vehicle + cargo/locus). Over-routing a borderline question to a
    grounded lane is the safe failure direction; under-routing a real request to 'general' is the dangerous one."""
    genes = [g for g in _GENE_RE.findall(message) if g not in {"DNA", "RNA", "AAV", "LNP", "HSV", "CAR", "RNP", "PEG"}]
    signals = sum(bool(x) for x in (_VEHICLE.search(message), _LOCUS.search(message), _CELL.search(message),
                                    _CARGO.search(message), genes))
    if _ACTION.search(message):
        return signals >= 1
    # no action verb: a noun-phrase design needs a vehicle + a cargo/locus ("AAV delivery of a 3 kb cassette")
    return bool(_VEHICLE.search(message)) and bool(_CARGO.search(message) or _LOCUS.search(message))


def classify(message: str, history: list | None = None) -> str:
    msg = (message or "").strip()
    has_history = bool(history)
    if _looks_like_design(msg):
        return "design"
    if has_history and _EXPLAIN.search(msg) and not _META.search(msg):
        return "explain"
    if _META.search(msg):
        return "meta"
    if _EXPLAIN.search(msg) and has_history: # follow-up interpretation even w/o explicit prior-number
        return "explain"
    # P-WS3 lane-aware memory: a back-reference follow-up to a GROUNDED answer (design/explain/meta) stays grounded
    # in the explain lane rather than silently downgrading to the (now retrieval-gated) general lane.
    if _prior_lane(history) in ("design", "explain", "meta") and _FOLLOWUP.search(msg) and not _GREETING.search(msg):
        return "explain"
    return "general"


# topic -> (PEN-STACK module, an example you can actually run)
_ANGLES = [
    (re.compile(r"\b(vector|delivery|aav|lentivir|lnp|capsid|vehicle|serotype)\w*\b", re.I),
     "Delivery & Immunity", "compare AAV vs lentivirus for durable liver expression"),
    (re.compile(r"\b(safe[\s-]?harbo|locus|loci|integration site|where (to|can) (i )?(write|insert))\b", re.I),
     "Site Finder", "score safe-harbour loci for AAVS1 in hepatocytes"),
    (re.compile(r"\b(enzyme|writer|integrase|recombinase|nuclease|transposase|cas9|bxb1|paste|prime editor)\w*\b", re.I),
     "Writer Atlas", "which writer can integrate a 3 kb cassette at albumin in hepatocytes"),
    (re.compile(r"\b(immunogenic|immune|antibod|nab|seroprevalen|t[\s-]?cell|anti[\s-]?peg|genotox)\w*\b", re.I),
     "Delivery & Immunity", "immune-risk profile of an AAV insertion in adult liver"),
    (re.compile(r"\b(express|expression|durab|titer|outcome|how (well|much)|efficacy)\w*\b", re.I),
     "Digital Twin", "predict the relative outcome for an AAVS1 insertion in hepatocytes"),
    (re.compile(r"\b(safe|hazard|biosecurit|dual[\s-]?use|toxin|legal|allowed)\w*\b", re.I),
     "Guardian / Verify", "is it safe and legal to express factor IX from an AAV"),
]


def pen_stack_angles(message: str, limit: int = 2) -> list[dict]:
    """For a general question, which PEN-STACK modules could compute a concrete, grounded answer (+ an example)."""
    out, seen = [], set()
    for rx, module, example in _ANGLES:
        if rx.search(message) and module not in seen:
            out.append({"module": module, "example": example})
            seen.add(module)
        if len(out) >= limit:
            break
    return out
