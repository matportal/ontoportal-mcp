import asyncio

from mcp_client import OntoPortalMCPClient, default_mcp_url

async def main():
    client = OntoPortalMCPClient(default_mcp_url())
    async with client:
        tools = await client.list_tools()
        print(len(tools), tools[0].name)
        result = await client.call_tool("searchTerms", {"q": "heart"},
            raise_on_error=False)
        print(result.is_error, result.structured_content or result.content[0].text)

asyncio.run(main())
