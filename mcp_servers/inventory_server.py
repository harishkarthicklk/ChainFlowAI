
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp_servers.common import db, public_document

mcp = FastMCP("ChainFlow Inventory Server")


def now_utc():
    return datetime.now(timezone.utc)


@mcp.tool()
def check_stock(product_id: str) -> dict:
    """Check current stock, reserved quantity and available quantity."""

    inventory = db.inventory.find_one({"product_id": product_id})

    if not inventory:
        return {
            "success": False,
            "message": f"No inventory found for {product_id}."
        }

    return {
        "success": True,
        "inventory": public_document(inventory)
    }


@mcp.tool()
def reserve_stock(product_id: str, quantity: int) -> dict:
    """Reserve available stock without allowing the available quantity to go negative."""

    if quantity <= 0:
        return {
            "success": False,
            "message": "Quantity must be greater than zero."
        }

    result = db.inventory.update_one(
        {
            "product_id": product_id,
            "quantity_available": {"$gte": quantity}
        },
        {
            "$inc": {
                "quantity_available": -quantity,
                "quantity_reserved": quantity
            },
            "$set": {"updated_at": now_utc()}
        }
    )

    if result.modified_count == 0:
        inventory = db.inventory.find_one({"product_id": product_id})

        if not inventory:
            return {
                "success": False,
                "message": f"No inventory found for {product_id}."
            }

        return {
            "success": False,
            "message": "Insufficient available stock.",
            "available_quantity": inventory.get("quantity_available", 0)
        }

    updated = db.inventory.find_one({"product_id": product_id})

    return {
        "success": True,
        "message": f"Reserved {quantity} units.",
        "inventory": public_document(updated)
    }


@mcp.tool()
def update_inventory(
    product_id: str,
    quantity_received: int
) -> dict:
    """Add verified received units to stock. Does not verify shipment evidence itself."""

    if quantity_received <= 0:
        return {
            "success": False,
            "message": "Received quantity must be greater than zero."
        }

    result = db.inventory.update_one(
        {"product_id": product_id},
        {
            "$inc": {
                "quantity_on_hand": quantity_received,
                "quantity_available": quantity_received
            },
            "$set": {"updated_at": now_utc()}
        }
    )

    if result.matched_count == 0:
        return {
            "success": False,
            "message": f"No inventory found for {product_id}."
        }

    updated = db.inventory.find_one({"product_id": product_id})

    return {
        "success": True,
        "message": "Inventory updated. Ensure receipt was verified by the verification engine first.",
        "inventory": public_document(updated)
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
