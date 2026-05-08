from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from httpx import AsyncClient, Limits

from .api_types import MCP

class MCPHandler:
    def __init__(self, mcp_config : MCP):
        self.mcp_config = mcp_config
        self.headers = {
            "Authorization": f"Bearer {self.mcp_config.token}",
            "Content-Type": "application/json",
        }

    async def get_tools(self):
         async with AsyncClient(
            headers=self.headers,
            limits=Limits(max_connections=None, max_keepalive_connections=None),
            timeout=20.0
        ) as client:
            async with streamable_http_client(
                self.mcp_config.url,
                http_client=client
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    return tools_result.tools

    async def call_tool(self, tool_name, message):
        async with AsyncClient(
            headers=self.headers,
            limits=Limits(max_connections=None, max_keepalive_connections=None),
            timeout=20.0
        ) as client:
            async with streamable_http_client(
                self.mcp_config.url,
                http_client=client
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool(tool_name, message)

