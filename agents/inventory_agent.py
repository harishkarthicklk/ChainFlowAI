from agents.base_agent import MCPAgent


class InventoryAgent(MCPAgent):
    def __init__(self):
        super().__init__("Inventory Agent", "inventory")

    async def check_stock(self, product_id):
        return await self.call_tool(
            "check_stock", {"product_id": product_id}
        )

    async def reserve_stock(self, product_id, quantity):
        return await self.call_tool(
            "reserve_stock",
            {"product_id": product_id, "quantity": quantity},
        )

    async def update_inventory(self, product_id, quantity_received):
        return await self.call_tool(
            "update_inventory",
            {
                "product_id": product_id,
                "quantity_received": quantity_received,
            },
        )