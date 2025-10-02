"""Simple HTTP health check for the MCP server container."""

from __future__ import annotations

import os
import sys
import urllib.request


def main() -> int:
    port = os.getenv("MCP_PORT", "8083")
    url = os.getenv("HEALTHCHECK_URL", f"http://localhost:{port}/mcp")

    try:
        request = urllib.request.Request(
            url,
            method="POST",
            data=b"{}",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - health check
            if response.status in (200, 202):
                return 0
    except Exception:  # pragma: no cover - health check best effort
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
