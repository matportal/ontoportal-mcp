"""Client utilities for interacting with the OntoPortal MCP server."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx
from env_utils import load_env_file
from fastmcp import Client as FastMCPClient
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import ClientTransport, infer_transport
from fastmcp.exceptions import ToolError
from fastmcp.server.server import FastMCP
from mcp.types import Tool


class OntoPortalMCPClientError(Exception):
    """Base exception for client failures."""


class OntoPortalMCPAuthenticationError(OntoPortalMCPClientError):
    """Raised when authentication with the MCP server fails."""


class OntoPortalMCPToolError(OntoPortalMCPClientError):
    """Raised when a tool invocation fails on the server."""


@dataclass(slots=True)
class _TransportSpec:
    """Holds the information necessary to materialize a transport exactly once."""

    raw: str | FastMCP | ClientTransport
    token: str | None

    def build(self) -> ClientTransport:
        transport = infer_transport(self.raw)
        if self.token:
            try:
                transport._set_auth(self.token)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise OntoPortalMCPClientError(
                    "Authentication token provided but transport does not support auth"
                ) from exc
        return transport


def default_mcp_url() -> str:
    """Return the MCP server URL based on environment configuration."""

    load_env_file()
    env_url = os.getenv("ONTO_PORTAL_MCP_URL")
    if env_url:
        return env_url

    port = os.getenv("MCP_PORT", "8000")
    host = os.getenv("ONTO_PORTAL_MCP_CLIENT_HOST", "127.0.0.1")
    return f"http://{host}:{port}/mcp"


class OntoPortalMCPClient:
    """High-level wrapper around :class:`fastmcp.Client` with auth handling."""

    def __init__(
        self,
        transport: str | FastMCP | ClientTransport,
        *,
        token: str | None = None,
        timeout: float | int | None = None,
    ) -> None:
        self._transport_spec = _TransportSpec(raw=transport, token=token)
        self._timeout = timeout
        self._client: FastMCPClient | None = None
        self._transport: ClientTransport | None = None
        self._connected = False

    async def __aenter__(self) -> "OntoPortalMCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish a connection to the MCP server if not already connected."""

        if self._connected:
            return

        client = self._ensure_client()

        try:
            await client.__aenter__()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on server
            raise self._translate_http_error(exc) from exc

        self._connected = True

    async def disconnect(self) -> None:
        """Close the MCP connection if it is active."""

        if not self._connected or self._client is None:
            return

        await self._client.__aexit__(None, None, None)
        self._connected = False

    async def list_tools(self) -> list[Tool]:
        """Return the tools exposed by the server."""

        client = self._require_client()

        try:
            tools = await client.list_tools()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on server
            raise self._translate_http_error(exc) from exc
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | int | None = None,
        progress_handler: Any | None = None,
        raise_on_error: bool = True,
    ) -> CallToolResult:
        """Invoke a tool and return its :class:`~fastmcp.client.client.CallToolResult`."""

        client = self._require_client()

        try:
            return await client.call_tool(
                name=name,
                arguments=arguments or {},
                timeout=timeout,
                progress_handler=progress_handler,
                raise_on_error=raise_on_error,
            )
        except ToolError as exc:
            raise OntoPortalMCPToolError(str(exc)) from exc
        except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on server
            raise self._translate_http_error(exc) from exc

    def _ensure_client(self) -> FastMCPClient:
        if self._client is None:
            if self._transport is None:
                self._transport = self._transport_spec.build()
            self._client = FastMCPClient(self._transport, timeout=self._timeout)
        return self._client

    def _require_client(self) -> FastMCPClient:
        if not self._connected:
            raise RuntimeError("Client is not connected. Use 'async with' or connect().")
        return self._ensure_client()

    @staticmethod
    def _translate_http_error(error: httpx.HTTPStatusError) -> OntoPortalMCPClientError:
        status = error.response.status_code
        message = f"HTTP {status}: {error.response.reason_phrase}"
        if status in (401, 403):
            return OntoPortalMCPAuthenticationError(message)
        return OntoPortalMCPClientError(message)


__all__ = [
    "OntoPortalMCPClient",
    "OntoPortalMCPClientError",
    "OntoPortalMCPAuthenticationError",
    "OntoPortalMCPToolError",
    "default_mcp_url",
]
