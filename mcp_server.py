import logging
import os
from typing import Any, Mapping

import fastmcp
import httpx
import yaml
from env_utils import get_required_env, load_env_file
from fastmcp import FastMCP
from fastmcp.server import context as fastmcp_context
from fastmcp.server.middleware.middleware import Middleware
from fastmcp.server.middleware.middleware import MiddlewareContext

# Configure logging early so container logs capture diagnostics
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

# Load optional environment overrides
load_env_file()

# Load the OpenAPI specification
with open('openapi-small.yaml', 'r') as f:
    openapi_spec = yaml.safe_load(f)

# Create an HTTP client for the OntoPortal API
# The base URL is taken from the OpenAPI spec's servers section
# Override base URL as requested
DEFAULT_BASE_URL = get_required_env("ONTO_PORTAL_BASE_URL")
DEFAULT_API_KEY = get_required_env("ONTO_PORTAL_API_KEY")


class QueryParamMiddleware(Middleware):
    """Extract API key and base URL overrides from the MCP connection URL."""

    def __init__(self, default_api_key: str, default_base_url: str) -> None:
        self._default_api_key = default_api_key
        self._default_base_url = default_base_url

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next,
    ):  # type: ignore[override]
        if context.method == "initialize" and context.fastmcp_context is not None:
            fast_ctx = context.fastmcp_context
            request_ctx = fast_ctx.request_context
            request = getattr(request_ctx, "request", None)

            api_key = None
            base_url = None
            if request is not None:
                # Starlette Request exposes query_params mapping interface
                query = request.query_params  # type: ignore[attr-defined]
                api_key = (
                    query.get("api_key")
                    or query.get("apikey")
                    or query.get("token")
                )
                base_url = (
                    query.get("base_url")
                    or query.get("rest_url")
                    or query.get("rest_base_url")
                )

            session = request_ctx.session
            setattr(session, "ontoportal_api_key", api_key or self._default_api_key)
            setattr(session, "ontoportal_base_url", base_url or self._default_base_url)

        return await super().on_message(context, call_next)


class ContextAwareAsyncClient:
    """Wrapper that applies per-session overrides before delegating to httpx."""

    def __init__(self, default_base_url: str, default_api_key: str) -> None:
        self._default_base_url = httpx.URL(default_base_url)
        self._default_api_key = default_api_key
        self._client = httpx.AsyncClient()

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        ctx = fastmcp_context._current_context.get(None)  # type: ignore[attr-defined]
        session_api_key = None
        session_base_url = None
        if ctx is not None:
            request_ctx = ctx.request_context
            session = request_ctx.session
            session_api_key = getattr(session, "ontoportal_api_key", None)
            session_base_url = getattr(session, "ontoportal_base_url", None)

        api_key = session_api_key or self._default_api_key
        base_url = httpx.URL(session_base_url or str(self._default_base_url))

        logging.info(
            "OntoPortal client request start: method=%s url=%r session_base=%r session_api_key=%s",
            method,
            url,
            session_base_url,
            bool(session_api_key),
        )

        merged_headers: dict[str, str] = {}
        if headers:
            merged_headers.update(headers)
        # Always enforce the OntoPortal API key header
        merged_headers["Authorization"] = f"apikey token={api_key}"

        target_url = httpx.URL(url)
        if not target_url.is_absolute_url:
            logging.info(
                "Joining relative URL '%s' with base '%s' (session_base=%s)",
                target_url,
                base_url,
                session_base_url,
            )
            target_url = base_url.join(target_url)

        if not target_url.scheme:
            logging.error(
                "Resolved target URL lacks scheme: original=%r base=%r session_base=%r -> %r",
                url,
                base_url,
                session_base_url,
                target_url,
            )
            raise ValueError(
                "Resolved target URL lacks scheme",
            )

        logging.info(
            "HTTPX %s request %s -> %s (base=%s session_base=%s params=%s)",
            httpx.__version__,
            method,
            target_url,
            base_url,
            session_base_url,
            params,
        )

        return await self._client.request(
            method=method,
            url=target_url,
            headers=merged_headers,
            params=params,
            **kwargs,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # Expose other attributes as needed (e.g., for FastMCP shutdown routines)
    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)


client = ContextAwareAsyncClient(DEFAULT_BASE_URL, DEFAULT_API_KEY)


# Configure token authentication

# Create the MCP server from the OpenAPI spec
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="OntoPortal MCP Server"
)

# Enable query-parameter overrides for API key and base URL
mcp.add_middleware(QueryParamMiddleware(DEFAULT_API_KEY, DEFAULT_BASE_URL))


if __name__ == "__main__":
    fastmcp_version = getattr(fastmcp, "__version__", "unknown")
    logging.info(
        "Starting OntoPortal MCP with httpx=%s fastmcp=%s",
        httpx.__version__,
        fastmcp_version,
    )
    host = get_required_env("MCP_HOST")
    port = int(get_required_env("MCP_PORT"))
    mcp.run(transport="http", host=host, port=port)
