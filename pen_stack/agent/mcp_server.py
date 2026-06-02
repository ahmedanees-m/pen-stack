"""PEN-STACK MCP server (Phase 3, Step 3.10) — expose the validated tools to any external agent.

Wraps the Step-3.9 tools as a Model Context Protocol server (fastmcp) so any MCP client (Claude, etc.)
can call ``writability``, ``reachable_writers``, ``writer_axes``, ``plan_write``, ``ask_literature`` and
receive correct, provenance-tagged results — turning PEN-STACK into shared agentic infrastructure.

Run: ``python -m pen_stack.agent.mcp_server`` (needs the ``services`` extra: ``pip install fastmcp``).
"""
from __future__ import annotations

from pen_stack.agent import tools

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


if __name__ == "__main__":  # pragma: no cover
    mcp.run()
