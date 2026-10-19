
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.supplier_server"],
        env=os.environ.copy()
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print("-", tool.name)

            print("\n1. Creating test order...")
            result = await session.call_tool(
                "create_order",
                arguments={
                    "order_id": "ORD-TEST-0001",
                    "product_id": "DISPLAY-001",
                    "supplier_id": "SUPPLIER-001",
                    "destination_warehouse": "WAREHOUSE-001",
                    "quantity_ordered": 10,
                    "unit_price": 1500.0
                }
            )
            print(result)

            print("\n2. Confirming test order...")
            result = await session.call_tool(
                "confirm_order",
                arguments={"order_id": "ORD-TEST-0001"}
            )
            print(result)

            print("\n3. Requesting test shipment...")
            result = await session.call_tool(
                "request_shipment",
                arguments={
                    "order_id": "ORD-TEST-0001",
                    "shipment_id": "SHIP-TEST-0001"
                }
            )
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
