from agents.base_agent import MCPAgent


class FinanceAgent(MCPAgent):
    def __init__(self):
        super().__init__("Finance Agent", "finance")

    async def calculate_payable_amount(self, shipment_id):
        return await self.call_tool(
            "calculate_payable_amount",
            {"shipment_id": shipment_id},
        )

    async def request_payment_authorization(self, shipment_id):
        return await self.call_tool(
            "request_payment_authorization",
            {"shipment_id": shipment_id},
        )

    async def get_payment_status(self, shipment_id):
        return await self.call_tool(
            "get_payment_status",
            {"shipment_id": shipment_id},
        )