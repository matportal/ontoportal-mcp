# OntoPortal MCP Server

This project contains an MCP (Model Context Protocol) server for the OntoPortal API, generated from an OpenAPI specification using `fastmcp`. A lightweight async client (`mcp_client.py`) is included so you can exercise the server or integrate it into other tooling.

## Prerequisites

-   Python 3.6+
-   pip

## Installation

1.  **Install Dependencies**

    Install the necessary Python libraries using pip and the `requirements.txt` file:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Configuration values (OntoPortal base URL, API key, host/port) reside in `.env`. A template is provided in `.env.example`; copy it, adjust the values, and keep `.env` out of version control.

Start the Streamable HTTP MCP server (host and port come from `.env`):

```bash
.venv/bin/python mcp_server.py
```

The server will listen on the configured host/port (default `0.0.0.0:8000`) and forward tool calls to the OntoPortal REST API using the API key defined in `.env`.

### Docker Compose

Container images are provided via the included `Dockerfile` and `docker-compose.yml` for local development or quick smoke tests.

- Build and start the server:

  ```bash
  docker compose up --build server
  ```

- Run the smoke test (starts the server container, waits for it to become healthy, then executes `check_http_access.py` from a second container):

  ```bash
  docker compose up --build smoke
  ```

Override the host port via `HOST_MCP_PORT=9000 docker compose up server`. Update `.env` if you need different API credentials or want the containers to listen on another internal port.

## Client Usage

`OntoPortalMCPClient` wraps `fastmcp.Client`, handles Streamable HTTP transport setup, and optionally attaches a bearer token. Example usage (matches `test.py`):

```python
import asyncio
from mcp_client import OntoPortalMCPClient, default_mcp_url

async def main():
    client = OntoPortalMCPClient(default_mcp_url())
    async with client:
        tools = await client.list_tools()
        print(len(tools), tools[0].name)
        result = await client.call_tool("searchTerms", {"q": "heart"})
        print(result.structured_content["collection"][0]["prefLabel"])

asyncio.run(main())
```

Set the `token` parameter if the server expects a bearer credential (the current configuration does not enforce JWT verification).

### Passing configuration via the MCP URL

The server also accepts connection-specific overrides via query parameters on the MCP endpoint. This is useful when a client (e.g., Dify) can only provide credentials in the URL.

- `api_key`: OntoPortal API key that should be forwarded as `Authorization: apikey token=...`.
- `base_url`: OntoPortal REST base URL (defaults to `http://rest.matportal.org`).

Example URL (replace the port if you changed `MCP_PORT`):

```
http://your-server:8000/mcp?api_key=YOUR_KEY&base_url=https://rest.example.org
```

Each connection maintains its own overrides, so multiple clients can supply different keys or endpoints without restarting the server.

## Tests

The pytest suite uses live integration tests located in `tests/test_mcp_client.py`. They require a reachable MCP endpoint.

1. Start the server (see above) or provide a remote URL.
2. Optionally point the tests at a different server with `ONTO_PORTAL_MCP_URL` or set `MCP_PORT`/`ONTO_PORTAL_MCP_CLIENT_HOST`.
3. Run:

    ```bash
    .venv/bin/python -m pytest
    ```

If the server cannot be reached the tests are skipped so CI runs remain green when the endpoint is unavailable.

To perform a quick manual probe use:

```bash
.venv/bin/python check_http_access.py --url "http://server:YOUR_PORT/mcp"
```

## Authentication

The server forwards requests to OntoPortal with an API key supplied via HTTP headers. If you enable bearer authentication on the MCP server in the future, pass the token via `OntoPortalMCPClient(token="<jwt>")` or set the `Authorization` header manually when invoking tools from another client.

`generate_token.py` remains available for creating sample JWTs should you reintroduce JWT verification.
