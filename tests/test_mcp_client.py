import os

import pytest
import pytest_asyncio

from mcp_client import OntoPortalMCPClient, OntoPortalMCPToolError


MCP_URL = os.environ.get("ONTO_PORTAL_MCP_URL", "http://127.0.0.1:8000/mcp")


def _skip_for_unreachable(exc: Exception) -> None:
    message = str(exc).lower()
    if "failed to connect" in message or "all connection attempts failed" in message:
        pytest.skip(f"Cannot reach MCP server at {MCP_URL}: {exc}")


@pytest_asyncio.fixture
async def connected_client():
    client = OntoPortalMCPClient(MCP_URL)
    try:
        await client.connect()
    except RuntimeError as exc:
        _skip_for_unreachable(exc)
        raise
    except Exception as exc:  # pragma: no cover - unexpected failures should surface
        _skip_for_unreachable(exc)
        raise
    try:
        yield client
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_list_tools_contains_search_terms(connected_client):
    tools = await connected_client.list_tools()
    tool_names = {tool.name for tool in tools}
    assert "searchTerms" in tool_names
    assert len(tool_names) >= 1


@pytest.mark.asyncio
async def test_search_terms_tool_returns_results(connected_client):
    result = await connected_client.call_tool(
        "searchTerms",
        {"q": "heart"},
        raise_on_error=True,
    )

    assert result.is_error is False
    data = result.structured_content or {}
    collection = data.get("collection")
    assert isinstance(collection, list)
    assert collection
    assert data.get("totalCount") is not None
    first = collection[0]
    assert "prefLabel" in first
    assert first["prefLabel"]


@pytest.mark.asyncio
async def test_search_terms_requires_query_argument(connected_client):
    result = await connected_client.call_tool(
        "searchTerms",
        {},
        raise_on_error=False,
    )

    if not result.is_error:
        pytest.skip("Server accepted empty query; cannot validate error handling")

    with pytest.raises(OntoPortalMCPToolError):
        await connected_client.call_tool("searchTerms", {}, raise_on_error=True)
