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
except ImportError as e:  # pragma: no cover - services extra optional
    raise ImportError("fastmcp not installed: pip install 'pen-stack[services]'") from e

mcp = FastMCP("pen-stack")

# register each validated tool (the same functions the in-process agent and the eval harness use)
mcp.tool()(tools.writability)
mcp.tool()(tools.reachable_writers)
mcp.tool()(tools.writer_axes)
mcp.tool()(tools.plan_write)
mcp.tool()(tools.ask_literature)
mcp.tool()(tools.multiplex_translocation_risk)            # WS-G1: multiplex translocation-risk screen


@mcp.tool()
def plan_write_session(gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562",
                       payload_seq: str | None = None, mode: str = "automatic") -> dict:
    """PEN-Agent: grounded write-planning state machine (site -> writer -> cargo+polish -> off-target -> 3D).

    Every number is copied from a tool result with provenance; ungrounded steps degrade/refuse, never
    fabricate. Modes: automatic | guided | qa."""
    return pen_agent.plan_write_session(gene, intent, cargo_bp=cargo_bp, ct=ct,
                                        payload_seq=payload_seq, mode=mode)


if __name__ == "__main__":  # pragma: no cover
    mcp.run()
