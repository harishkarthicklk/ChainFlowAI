from agents.base_agent import MCPAgent


class SupplierAgent(MCPAgent):
    def __init__(self):
        super().__init__("Supplier Agent", "supplier")

    async def create_order(self, **kwargs):
        return await self.call_tool("create_order", kwargs)

    async def confirm_order(self, order_id):
        return await self.call_tool(
            "confirm_order", {"order_id": order_id}
        )

    async def request_shipment(self, order_id, shipment_id):
        return await self.call_tool(
            "request_shipment",
            {"order_id": order_id, "shipment_id": shipment_id},
        )