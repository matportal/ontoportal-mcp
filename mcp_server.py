import os
from pathlib import Path

import httpx
import yaml
from fastmcp import FastMCP


def load_env_file(path: str = ".env") -> None:
    """Simple .env loader to avoid external dependencies."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

# Enable the new OpenAPI parser
os.environ['FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER'] = 'true'

# Load optional environment overrides
load_env_file()

# Load the OpenAPI specification
with open('openapi-small.yaml', 'r') as f:
    openapi_spec = yaml.safe_load(f)

# Create an HTTP client for the OntoPortal API
# The base URL is taken from the OpenAPI spec's servers section
# Override base URL as requested
base_url = os.getenv("ONTO_PORTAL_BASE_URL", "http://rest.matportal.org")
# Configure default Authorization header for OntoPortal API
api_key = os.getenv(
    "ONTO_PORTAL_API_KEY",
    "60eab942-ece4-4cd0-a15a-0fc8b1d70c52",
)
headers = {"Authorization": f"apikey token={api_key}"}
client = httpx.AsyncClient(base_url=base_url, headers=headers)


# Configure token authentication

# Create the MCP server from the OpenAPI spec
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="OntoPortal MCP Server"
)


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)
