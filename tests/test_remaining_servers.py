
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server(module_name, calls):
    print(f"\n{'=' * 60}")
    print(f"Testing: {module_name}")
    print("=" * 60)

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", module_name],
        env=os.environ.copy(),
        cwd=r"C:\ChainFlowAI"
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]

            print("Discovered tools:", names)

            for tool_name, arguments in calls:
                print(f"\nCalling {tool_name}...")
                result = await session.call_tool(
                    tool_name,
                    arguments=arguments
                )

                for item in result.content:
                    if hasattr(item, "text"):
                        print(item.text)

                if result.isError:
                    raise RuntimeError(
                        f"MCP tool returned an error: {tool_name}"
                    )


async def main():
    # Use the existing test shipment created by the supplier-server test.
    shipment_id = "SHIP-TEST-0001"

    await test_server(
        "mcp_servers.warehouse_server",
        [
            ("record_scan_count", {
                "shipment_id": shipment_id,
                "scanned_quantity": 10
            }),
            ("record_weight_measurement", {
                "shipment_id": shipment_id,
                "estimated_quantity": 10
            }),
            ("submit_receipt_evidence", {
                "shipment_id": shipment_id,
                "received_quantity": 10
            })
        ]
    )

    await test_server(
        "mcp_servers.logistics_server",
        [
            ("create_shipment", {
                "order_id": "ORD-TEST-0001",
                "shipment_id": shipment_id
            }),
            ("update_tracking_status", {
                "shipment_id": shipment_id,
                "tracking_status": "IN_TRANSIT"
            }),
            ("get_shipment_status", {
                "shipment_id": shipment_id
            })
        ]
    )

    # Use the real sample display shipment for finance tests.
    # Its verification is still PENDING, so authorization should be blocked.
    display_shipment_id = "SHIP-2026-0002"

    await test_server(
        "mcp_servers.finance_server",
        [
            ("calculate_payable_amount", {
                "shipment_id": display_shipment_id
            }),
            ("request_payment_authorization", {
                "shipment_id": display_shipment_id
            }),
            ("get_payment_status", {
                "shipment_id": display_shipment_id
            })
        ]
    )

    print("\nAll three MCP servers completed their test calls.")


if __name__ == "__main__":
    asyncio.run(main())
