"""Cloud-lab connector (v7.0, Stage J, J-WS1): safety-gated export -> a cloud-lab submission -> gated ingest.

Bridges the build interface to a cloud lab (Ginkgo / Emerald / Strateos style). The HARD invariant: the
biosecurity gate runs BEFORE any submission. A flagged or illegal design makes ``export_protocol`` raise, so no
protocol is emitted and nothing hazardous can be submitted through the loop. Submission is mock / dry-run for
v7.0 (the executable spec is the deliverable; a real wet run needs a partner and budget, the standing
bottleneck, surfaced not hidden). A returned readout is ingested only through an explicit human-in-control gate
(Level 3). Nothing is fabricated: a mock job carries a deterministic receipt, never a pretend measurement.
"""
from __future__ import annotations

import hashlib
from typing import Any

from pen_stack.build.protocol import ProtocolExportError, export_protocol

# mock is the only provider WIRED (a local dry-run receipt). The named providers are recognised but route to the
# mock path, since a real submission needs credentials + budget (disclosed, not faked).
_PROVIDERS = {"mock", "ginkgo", "emerald", "strateos"}


class CloudLabError(RuntimeError):
    """Raised for a connector-level error (unknown provider, etc.). Safety refusals raise ProtocolExportError."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def submit(design: dict, experiment: dict, *, provider: str = "mock", target: str = "opentrons",
           actor: str = "anonymous") -> dict[str, Any]:
    """Safety-gate + export a protocol and submit it to a cloud lab (mock / dry-run).

    HARD GATE: ``export_protocol`` refuses a flagged or illegal design (raises ``ProtocolExportError``); we let it
    raise, so a hazardous design never reaches submission. Returns a mock job receipt for a cleared design.
    """
    if provider not in _PROVIDERS:
        raise CloudLabError(f"unknown provider {provider!r}; choose from {sorted(_PROVIDERS)}")
    protocol = export_protocol(design, experiment, target=target, actor=actor)  # biosecurity gate; may raise
    sha = _digest(protocol)
    return {
        "provider": provider,
        "dry_run": True,
        "status": "submitted_mock",
        "job_id": f"{provider}-{sha[:16]}",
        "protocol_sha256": sha,
        "protocol_preview": protocol[:400],
        "biosecurity_gate": "passed (export not blocked)",
        "autonomy_level": 3,
        "human_in_control": True,
        "note": ("mock / dry-run submission; a real cloud-lab run needs a partner + budget (the standing "
                 "bottleneck). The executable protocol is the deliverable."),
    }


def submit_gated(design: dict, experiment: dict, **kw: Any) -> dict[str, Any]:
    """Like :func:`submit`, but returns a STRUCTURED refusal instead of raising when the gate blocks the design,
    so an agent can branch on it (``blocked == True``). A blocked design emits NO protocol."""
    try:
        return submit(design, experiment, **kw)
    except ProtocolExportError as e:
        return {"submitted": False, "blocked": True, "reason": str(e),
                "biosecurity_gate": "blocked export (refused)", "human_in_control": True,
                "note": "the biosecurity gate refused this design; nothing was submitted"}


def ingest_readout(job_id: str, readout: dict, *, admitted_by: str | None = None) -> dict[str, Any]:
    """Ingest a cloud-lab readout through the Level-3 human-in-control gate. Requires ``admitted_by`` (a human
    approves belief admission); a readout with no approver is held, never auto-admitted. Never fabricated."""
    if not admitted_by:
        return {"job_id": job_id, "admitted": False, "held": True,
                "note": "a human must admit this readout (Level-3 belief-admission gate); not auto-admitted"}
    return {"job_id": job_id, "admitted": True, "admitted_by": admitted_by, "readout": readout,
            "autonomy_level": 3, "human_in_control": True, "no_fabrication": True}
