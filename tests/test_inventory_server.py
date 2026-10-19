
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.inventory_server"],
        env=os.environ.copy(),
        cwd=r"C:\ChainFlowAI"
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available inventory tools:")
            for tool in tools.tools:
                print("-", tool.name)

            print("\nChecking battery stock...")
            result = await session.call_tool(
                "check_stock",
                arguments={"product_id": "BATTERY-001"}
            )
            print(result)

            print("\nChecking display stock...")
            result = await session.call_tool(
                "check_stock",
                arguments={"product_id": "DISPLAY-001"}
            )
            print(result)

            print("\nTesting insufficient-stock protection...")
            result = await session.call_tool(
                "reserve_stock",
                arguments={
                    "product_id": "DISPLAY-001",
                    "quantity": 999999999
                }
            )
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
