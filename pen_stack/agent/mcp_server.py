"""PEN-STACK MCP server (Phase 3, Step 3.10; v3.1 WS-E2) - expose the validated capabilities to any agent.

Wraps the validated tools as a Model Context Protocol server (fastmcp) so any MCP client (Claude, etc.)
can call ``writability``, ``reachable_writers``, ``writer_axes``, ``plan_write``, ``ask_literature`` and the
grounded ``plan_write_session`` (the full PEN-Agent state machine) and receive correct, provenance-tagged
results - turning PEN-STACK into shared agentic infrastructure.

Run: ``python -m pen_stack.agent.mcp_server`` (needs the ``services`` extra: ``pip install fastmcp``).
"""
from __future__ import annotations

from pen_stack.agent import pen_agent, tools

try:
    from fastmcp import FastMCP
except ImportError as e: # pragma: no cover - services extra optional
    raise ImportError("fastmcp not installed: pip install 'pen-stack[services]'") from e

mcp = FastMCP("pen-stack")

# register each validated tool (the same functions the in-process agent and the eval harness use)
mcp.tool()(tools.writability)
mcp.tool()(tools.reachable_writers)
mcp.tool()(tools.writer_axes)
mcp.tool()(tools.plan_write)
mcp.tool()(tools.ask_literature)
mcp.tool()(tools.multiplex_translocation_risk) # WS-G1: multiplex translocation-risk screen


@mcp.tool()
def plan_write_session(gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562",
                       payload_seq: str | None = None, mode: str = "automatic") -> dict:
    """PEN-Agent: grounded write-planning state machine (site -> writer -> cargo+polish -> off-target -> 3D).

    Every number is copied from a tool result with provenance; ungrounded steps degrade/refuse, never
    fabricate. Modes: automatic | guided | qa."""
    return pen_agent.plan_write_session(gene, intent, cargo_bp=cargo_bp, ct=ct,
                                        payload_seq=payload_seq, mode=mode)


@mcp.tool()
def verify_write(design: dict) -> dict:
    """v3.3 verifier (WS-V): submit a proposed genomic write as a dict (write_type, writer_family, site_seq,
    cargo_bp, delivery_vehicle, cell_type, edit_intent, no_integration, target_guide/donor_guide, edits, ...)
    and get back a Verdict: legal/illegal + the named violated rule(s) + citation, a calibrated confidence on
    the soft components, an epistemic status, and any out-of-scope flags. Legality and confidence are distinct
    axes; every number traces to a tool (no fabrication). Unsupported write types defer."""
    from pen_stack.verify import verify
    return verify(design).model_dump()


@mcp.tool()
def graph_query(locus: str, cargo_form: str | None = None) -> dict:
    """v4.5 world-model graph (WS-G): a multi-hop query. Returns the writer families that REACH `locus` AND
    are DELIVERABLE by a vehicle carrying `cargo_form` (optional), each answer with its provenanced edge path
    (the answer IS the path, no fabrication). The graph nodes/edges carry evidence kind + scope + provenance."""
    from pen_stack.graph import writers_reaching_and_deliverable
    return writers_reaching_and_deliverable(locus, cargo_form=cargo_form)


# ---- v6.1 the AI Integration Surface: self-describing resources + the engine tools ----
@mcp.resource("pen-stack://capabilities")
def capabilities_resource() -> dict:
    """WHAT PEN-STACK can do (machine-readable). An agent reads this and routes on it, not on prose."""
    from pen_stack.api.manifest import capability_manifest
    return capability_manifest()


@mcp.resource("pen-stack://scope")
def scope_resource() -> dict:
    """WHAT PEN-STACK REFUSES to answer: the known-unknowns + the oracle scope cards. The contract that makes
    depending on PEN-STACK safe, outputs outside scope are out_of_scope/extrapolating, never asserted."""
    from pen_stack.api.manifest import scope_manifest
    return scope_manifest()


@mcp.tool()
def safety_screen(design: dict) -> dict:
    """v5.7 Guardian: biosecurity / dual-use screen -> SafetyVerdict (clear/flag/escalate/refuse) + reason. A
    hazardous design returns a STRUCTURED refusal an agent can branch on (decision == 'refuse')."""
    from pen_stack.safety import safety_gate
    return safety_gate(design, actor=str(design.get("actor", "mcp"))).model_dump()


@mcp.tool()
def immune_profile(design: dict) -> dict:
    """v5.6 immune-risk profile: a per-axis screen (genotox/CD8/innate/NAb/anti-PEG), each with its own
    uncertainty + validation label. Never collapsed into one number (collapsed_score is None); magnitude is a
    declared known-unknown."""
    from pen_stack.planner.immune_profile import immune_profile as _ip
    return _ip(design)


@mcp.tool()
def offtarget_scan(writer_family: str, guide: str | None = None, candidate_sites: list | None = None,
                   sequence: str | None = None, assay: str = "guideseq") -> dict:
    """v6.10 PEN-OFFTGT cross-family off-target NOMINATION (NOT a clearance). Ranks candidate sites with a
    real-data mismatch-calibrated risk band + the real CRISOT learned score (nuclease), a pseudo-attB scan
    (integrase), or the Perry-DMS pseudosite engine (bridge); ships the validation assay that would confirm
    each candidate. Abstains without inputs; never fabricates sites."""
    from pen_stack.wgenome.offtarget_predict import nominate_offtargets
    return nominate_offtargets(writer_family, guide=guide, candidate_sites=candidate_sites,
                               sequence=sequence, assay=assay)


@mcp.tool()
def delivery_recommend(cargo_form: str, cargo_bp: int | None = None, target_tissue: str | None = None,
                       safety_weight: float = 0.5, in_vivo: bool | None = None) -> dict:
    """v6.11 PEN-DELIVER cross-modality delivery recommender: rank vehicles by cargo-form + safety<->efficacy + a
    GROUNDED serotype->tissue tropism prior (from approved AAV therapies; a known-unknown for novel capsids), plus
    the learned FLIP-AAV capsid-fitness capability. Never fabricates tropism; abstains without inputs."""
    from pen_stack.planner.delivery_predict import recommend_delivery_plus
    return recommend_delivery_plus(cargo_form, cargo_bp, target_tissue, safety_weight=safety_weight, in_vivo=in_vivo)


@mcp.tool()
def generate_designs(goal: dict | None = None, candidates: list | None = None, keep: int = 25) -> dict:
    """v5.8 generative designer (verifier-as-discriminator): hazardous/illegal candidates are DISCARDED;
    survivors are calibrated + immune-profiled CANDIDATES (never asserted to work)."""
    from pen_stack.design import generate_designs as _gd
    return {"survivors": _gd(goal, candidates=candidates, keep=keep, actor="mcp")}


@mcp.tool()
def predict_outcome(design: dict, cell_state: str = "k562") -> dict:
    """v5.9 digital twin: a calibrated, OOD-gated, phenotype-bounded outcome (interval + scope flags). A
    candidate prediction, never the truth; phenotype/in-vivo magnitude stay out of scope."""
    from pen_stack.twin import predict_outcome as _po
    return _po(design, cell_state)


@mcp.tool()
def suggest_experiment(candidates: list, cell_state: str = "k562", k: int = 8) -> dict:
    """v5.10 experiment designer: a diverse, informative next-experiment batch (EIG + immune-VOI), each with
    its expected information gain."""
    from pen_stack.active import select_batch
    return {"batch": select_batch(candidates, cell_state, {}, k=k)}


@mcp.tool()
def co_scientist_session(goal: dict, cell_state: str = "k562") -> dict:
    """v5.13 co-scientist: drive the full loop -> Pareto strategies + calibrated outcomes + per-axis immune
    profiles + suggested experiments + citations + scope ledger + safety. The scientist decides; this drives."""
    from pen_stack.agent.co_scientist import co_scientist_session as _cs
    return _cs(goal, cell_state)


if __name__ == "__main__": # pragma: no cover
    mcp.run()
