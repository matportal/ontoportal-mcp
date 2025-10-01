"""Simple probe to verify the MCP server is reachable over HTTP."""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Optional

from mcp_client import OntoPortalMCPClient


async def check_access(url: str, token: Optional[str]) -> None:
    client = OntoPortalMCPClient(url, token=token)
    try:
        async with client:
            tools = await client.list_tools()
            print(f"✅ Connected to {url}")
            print(f"   Available tools: {len(tools)} (first: {tools[0].name if tools else 'none'})")
            result = await client.call_tool(
                "searchTerms",
                {"q": "heart"},
                raise_on_error=False,
            )
            if result.is_error:
                print(f"   searchTerms returned error: {result.content[0].text}")
            else:
                collection = result.structured_content.get("collection", []) if result.structured_content else []
                print(f"   searchTerms returned {len(collection)} results")
    except Exception as exc:  # pragma: no cover - diagnostics script
        print(f"❌ Failed to reach {url}: {exc}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Check MCP server HTTP accessibility")
    parser.add_argument(
        "--url",
        default=os.getenv("ONTO_PORTAL_MCP_URL", "http://127.0.0.1:8000/mcp"),
        help="MCP server URL (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ONTO_PORTAL_MCP_TOKEN"),
        help="Optional bearer token to include in requests",
    )
    args = parser.parse_args()

    asyncio.run(check_access(args.url, args.token))


if __name__ == "__main__":
    main()
