
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp_servers.common import db, public_document

mcp = FastMCP("ChainFlow Logistics Server")

ALLOWED_STATUSES = {
    "SHIPMENT_REQUESTED",
    "READY_FOR_DISPATCH",
    "IN_TRANSIT",
    "ARRIVED_AT_WAREHOUSE",
    "RECEIVED",
    "DELIVERED",
    "DELAYED",
    "CANCELLED"
}


def now_utc():
    return datetime.now(timezone.utc)


@mcp.tool()
def create_shipment(order_id: str, shipment_id: str) -> dict:
    """Create a shipment for a confirmed order, or return its existing shipment."""

    order = db.orders.find_one({"_id": order_id})
    if not order:
        return {"success": False, "message": "Order not found."}

    if order.get("status") != "CONFIRMED":
        return {"success": False, "message": "Order must be confirmed first."}

    existing = db.shipments.find_one({"_id": shipment_id})
    if existing:
        if existing.get("order_id") != order_id:
            return {
                "success": False,
                "message": "Shipment ID belongs to a different order."
            }

        return {
            "success": True,
            "message": "Shipment already exists.",
            "shipment": public_document(existing)
        }

    other_shipment = db.shipments.find_one({"order_id": order_id})
    if other_shipment:
        return {
            "success": False,
            "message": "Order already has a shipment.",
            "existing_shipment_id": other_shipment["_id"]
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
        "message": "Shipment created; verification remains pending.",
        "shipment": public_document(shipment)
    }


@mcp.tool()
def update_tracking_status(
    shipment_id: str,
    tracking_status: str
) -> dict:
    """Update shipment tracking status without approving verification or payment."""

    if tracking_status not in ALLOWED_STATUSES:
        return {
            "success": False,
            "message": "Unsupported tracking status.",
            "allowed_statuses": sorted(ALLOWED_STATUSES)
        }

    shipment = db.shipments.find_one({"_id": shipment_id})
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    db.shipments.update_one(
        {"_id": shipment_id},
        {
            "$set": {
                "tracking_status": tracking_status,
                "updated_at": now_utc()
            }
        }
    )

    updated = db.shipments.find_one({"_id": shipment_id})

    return {
        "success": True,
        "message": "Tracking status updated. Verification status is unchanged.",
        "shipment": public_document(updated)
    }


@mcp.tool()
def get_shipment_status(shipment_id: str) -> dict:
    """Retrieve tracking, verification and payment status for a shipment."""

    shipment = db.shipments.find_one({"_id": shipment_id})

    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    return {
        "success": True,
        "shipment": public_document(shipment)
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
