from agents.base_agent import MCPAgent


class LogisticsAgent(MCPAgent):
    def __init__(self):
        super().__init__("Logistics Agent", "logistics")

    async def create_shipment(self, order_id, shipment_id):
        return await self.call_tool(
            "create_shipment",
            {"order_id": order_id, "shipment_id": shipment_id},
        )

    async def update_tracking_status(self, shipment_id, tracking_status):
        return await self.call_tool(
            "update_tracking_status",
            {
                "shipment_id": shipment_id,
                "tracking_status": tracking_status,
            },
        )

    async def get_shipment_status(self, shipment_id):
        return await self.call_tool(
            "get_shipment_status", {"shipment_id": shipment_id}
        )