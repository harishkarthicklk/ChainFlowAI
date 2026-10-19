
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp_servers.common import db, public_document

mcp = FastMCP("ChainFlow Supplier Order Server")


def now_utc():
    return datetime.now(timezone.utc)


@mcp.tool()
def create_order(
    order_id: str,
    product_id: str,
    supplier_id: str,
    destination_warehouse: str,
    quantity_ordered: int,
    unit_price: float
) -> dict:
    """Create a draft order after validating product, quantity and price."""

    if quantity_ordered <= 0 or unit_price <= 0:
        return {"success": False, "message": "Quantity and price must be positive."}

    if db.orders.find_one({"_id": order_id}):
        return {"success": False, "message": f"Order {order_id} already exists."}

    product = db.products.find_one({"_id": product_id})
    if not product:
        return {"success": False, "message": f"Product {product_id} was not found."}

    inventory = db.inventory.find_one({"product_id": product_id})
    if not inventory:
        return {"success": False, "message": "No inventory record exists for this product."}

    if inventory.get("quantity_available", 0) < quantity_ordered:
        return {
            "success": False,
            "message": "Insufficient available inventory.",
            "available": inventory.get("quantity_available", 0)
        }

    order = {
        "_id": order_id,
        "product_id": product_id,
        "supplier_id": supplier_id,
        "destination_warehouse": destination_warehouse,
        "quantity_ordered": quantity_ordered,
        "unit_price": float(unit_price),
        "currency": "INR",
        "status": "DRAFT",
        "created_at": now_utc()
    }

    db.orders.insert_one(order)

    return {
        "success": True,
        "message": "Order created.",
        "order": public_document(order)
    }


@mcp.tool()
def confirm_order(order_id: str) -> dict:
    """Confirm an existing draft order."""

    order = db.orders.find_one({"_id": order_id})

    if not order:
        return {"success": False, "message": f"Order {order_id} was not found."}

    if order.get("status") == "CONFIRMED":
        return {"success": True, "message": "Order is already confirmed."}

    if order.get("status") != "DRAFT":
        return {
            "success": False,
            "message": f"Cannot confirm an order in status {order.get('status')}."
        }

    db.orders.update_one(
        {"_id": order_id, "status": "DRAFT"},
        {"$set": {"status": "CONFIRMED", "confirmed_at": now_utc()}}
    )

    updated = db.orders.find_one({"_id": order_id})

    return {
        "success": True,
        "message": "Order confirmed.",
        "order": public_document(updated)
    }


@mcp.tool()
def request_shipment(order_id: str, shipment_id: str) -> dict:
    """Create a pending-verification shipment for a confirmed order."""

    order = db.orders.find_one({"_id": order_id})

    if not order:
        return {"success": False, "message": f"Order {order_id} was not found."}

    if order.get("status") != "CONFIRMED":
        return {
            "success": False,
            "message": "Only confirmed orders can request a shipment."
        }

    existing = db.shipments.find_one({"_id": shipment_id})
    if existing:
        return {
            "success": False,
            "message": f"Shipment {shipment_id} already exists."
        }

    existing_for_order = db.shipments.find_one({"order_id": order_id})
    if existing_for_order:
        return {
            "success": False,
            "message": "This order already has a shipment.",
            "existing_shipment_id": existing_for_order["_id"]
        }

    now = now_utc()
    shipment = {
        "_id": shipment_id,
        "order_id": order_id,
        "product_id": order["product_id"],
        "quantity_claimed": order["quantity_ordered"],
        "quantity_received": None,
        "origin": order["supplier_id"],
        "destination": order["destination_warehouse"],
        "tracking_status": "SHIPMENT_REQUESTED",
        "verification_status": "PENDING",
        "payment_status": "ON_HOLD",
        "created_at": now,
        "updated_at": now
    }

    db.shipments.insert_one(shipment)

    return {
        "success": True,
        "message": "Shipment requested. Verification is still pending.",
        "shipment": public_document(shipment)
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
