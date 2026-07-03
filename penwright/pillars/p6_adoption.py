"""P6 — adoption signal (the YC move), generated honestly.

The battle plan calls for an adoption signal: a concrete deployment story and, ideally, a soft "a real lab /
biotech would use this" from a collaborator. This module renders a one-page adoption brief grounded in what
the system actually does (the golden-path deliverable), with the collaborator quote left as an EXPLICIT,
clearly-labelled placeholder — it is not fabricated. Filling it requires a real conversation; the brief makes
the ask precise so that conversation is easy to have.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_PLACEHOLDER = ("[[ ADOPTION QUOTE — PLACEHOLDER. To be filled by a named collaborator (a CMC/analytical or "
                "Gladstone-adjacent gene-therapy scientist). NOT fabricated; left blank until a real person "
                "says it on the record. ]]")

_BRIEF = """# PENWRIGHT — Adoption Brief (P6)

> One line: PENWRIGHT turns a plain-English gene-therapy goal into a safety-cleared, evidence-cited,
> outcome-validated genome-writing design dossier — autonomously, and without fabricating a single number.

## Who uses it, and for what
**User:** a gene-therapy / genome-engineering scientist scoping a durable, safe edit (e.g. a CAR construct
into a T-cell safe-harbour locus) who today hops across a dozen tools over days-to-weeks per candidate.

**Job replaced:** the manual loop of locus shortlisting → enzyme selection → off-target screening →
immunogenicity checks → biosecurity review → "what do I run next". PENWRIGHT runs that loop end to end in one
pass, self-corrects across rounds, hard-gates the hazardous variants, and hands back an auditable dossier plus
the single highest-information next experiment.

## Why a lab would adopt it (the concrete pull)
1. **It is governed, so it can be trusted to run autonomously.** The enforcing bio-firewall refuses hazardous
   requests *first* and short-circuits; every number traces to a validated tool or an OOD-gated oracle. The
   no-fabrication invariant is shown, not claimed.
2. **It closes the loop, not one step.** Design → enforced safety → off-target → evidence → calibration
   critique → redesign → convergence → next experiment — the whole thing, legibly.
3. **It is honest about what it does not know.** Data-gated axes are reported as calibrated proxies or honest
   nulls, never as a manufactured checkmark — the property a regulated-adjacent lab actually needs.
4. **It emits a signed, tamper-evident design passport** — an audit artifact an IBC / QA reviewer can verify.

## Deployment story (concrete, low-friction)
- **Form factor:** a self-hostable service (`docker compose up`) — REST API + web co-scientist + MCP server —
  that a lab runs behind its own firewall on public data; no PHI, no cloud dependency required.
- **Day-one use:** paste a therapeutic goal, get a dossier + passport; the lab decides, the co-scientist
  drives and presents.
- **Integration:** the experiment designer already emits a cloud-lab-submittable spec; the build interface is
  safety-gated (draft only, never auto-run).

## The ask (what turns this brief into a real P6 signal)
A 20-minute call with one gene-therapy scientist to (a) run their real goal through the golden path and
(b) say, on the record, whether they would use it and for what. Target: a CMC/analytical or a
Gladstone-adjacent (Pollard-lab DNA-regulatory-activity) collaborator, given the durability-axis narrative.

## Collaborator quote
{quote}

---
*Honesty note: the deployment mechanics above are real (they describe the shipped system). The collaborator
quote is a labelled placeholder and must not be presented as obtained until a named person provides it.*
"""


def run(out_dir: str = "out/penwright") -> dict[str, Any]:
    """Render the adoption brief with an explicit, unfilled quote placeholder. Returns a summary."""
    os.makedirs(out_dir, exist_ok=True)
    brief = _BRIEF.format(quote=_PLACEHOLDER)
    path = os.path.join(out_dir, "p6_adoption.md")
    Path(path).write_text(brief, encoding="utf-8")
    return {
        "pillar": "P6",
        "artifact": path,
        "quote_obtained": False,
        "quote_status": "placeholder — not fabricated; requires a named collaborator on the record",
        "deployment_story_real": True,
        "headline": ("Adoption brief rendered from the real shipped system; the collaborator quote is a "
                     "labelled placeholder (not fabricated) with a precise ask to obtain it."),
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(run(), indent=2))
