"""Minimal MCP client — call PEN-STACK over the Model Context Protocol (PEN-STACK v6.1, WS-EXAMPLE).

Lists the tools + the self-describing resources (`pen-stack://capabilities`, `pen-stack://scope`), reads the
scope (what PEN-STACK refuses to answer), then calls `verify_write` and branches on the structured verdict — the
same honest contract as REST, over MCP.

Run the server in one terminal:  python -m pen_stack.agent.mcp_server   (needs the `services` extra: fastmcp)
Then:                            python examples/mcp_client.py
"""
from __future__ import annotations

import asyncio


async def main() -> None:
    from fastmcp import Client                                # pip install 'pen-stack[services]'
    async with Client("pen_stack/agent/mcp_server.py") as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools])
        resources = await client.list_resources()
        print("resources:", [str(r.uri) for r in resources])

        scope = await client.read_resource("pen-stack://scope")   # what PEN-STACK won't answer
        print("known-unknowns:", len(scope[0].text))

        design = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19",
                  "delivery_vehicle": "AAV_single", "cargo_bp": 3000, "cargo_function": "ricin-like RIP",
                  "pfam_domains": ["PF00161"]}
        verdict = await client.call_tool("verify_write", {"design": design})
        print("hazardous design -> safety:", verdict.data.get("safety", {}).get("decision"))   # 'refuse'


if __name__ == "__main__":
    asyncio.run(main())
