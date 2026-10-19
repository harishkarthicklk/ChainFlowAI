from agents.base_agent import MCPAgent


class WarehouseAgent(MCPAgent):
    def __init__(self):
        super().__init__("Warehouse Agent", "warehouse")

    async def record_scan_count(self, shipment_id, scanned_quantity):
        return await self.call_tool(
            "record_scan_count",
            {
                "shipment_id": shipment_id,
                "scanned_quantity": scanned_quantity,
            },
        )

    async def record_weight_measurement(
        self, shipment_id, estimated_quantity
    ):
        return await self.call_tool(
            "record_weight_measurement",
            {
                "shipment_id": shipment_id,
                "estimated_quantity": estimated_quantity,
            },
        )

    async def submit_receipt_evidence(
        self, shipment_id, received_quantity
    ):
        return await self.call_tool(
            "submit_receipt_evidence",
            {
                "shipment_id": shipment_id,
                "received_quantity": received_quantity,
            },
        )