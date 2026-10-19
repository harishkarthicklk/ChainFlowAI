from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp_servers.common import db, public_document
from verification.safety_gate import require_transaction_approval

mcp = FastMCP("ChainFlow Finance Settlement Server")


def now_utc():
    return datetime.now(timezone.utc)


@mcp.tool()
def calculate_payable_amount(shipment_id: str) -> dict:
    """Calculate order value and check final transaction eligibility."""

    shipment = db.shipments.find_one({"_id": shipment_id})
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    order = db.orders.find_one({"_id": shipment["order_id"]})
    if not order:
        return {"success": False, "message": "Related order not found."}

    quantity = order.get("quantity_ordered", 0)
    unit_price = order.get("unit_price", 0.0)
    amount = round(quantity * unit_price, 2)

    eligible, reason = require_transaction_approval(shipment_id)

    return {
        "success": True,
        "shipment_id": shipment_id,
        "order_id": order["_id"],
        "ordered_quantity": quantity,
        "received_quantity": shipment.get("quantity_received"),
        "unit_price": unit_price,
        "currency": order.get("currency", "INR"),
        "calculated_order_value": amount,
        "payment_eligible": eligible,
        "message": (
            "Verification and manual approval passed. "
            "Transaction may proceed to the smart-contract stage."
            if eligible
            else f"Payment blocked: {reason}"
        ),
    }


@mcp.tool()
def request_payment_authorization(shipment_id: str) -> dict:
    """
    Record an authorization request only when verification and
    manual approval both pass. This does not transfer funds.
    """

    shipment = db.shipments.find_one({"_id": shipment_id})
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    order = db.orders.find_one({"_id": shipment["order_id"]})
    if not order:
        return {"success": False, "message": "Related order not found."}

    payment = db.payments.find_one({"shipment_id": shipment_id})
    if not payment:
        return {
            "success": False,
            "message": "Payment record not found.",
        }

    # Enforce the gate inside the Finance MCP server.
    eligible, reason = require_transaction_approval(shipment_id)

    if not eligible:
        return {
            "success": False,
            "message": f"Payment blocked: {reason}",
            "payment_status": payment.get("status", "ON_HOLD"),
            "authorized": False,
        }

    if payment.get("authorized") is True:
        return {
            "success": True,
            "message": "Payment is already marked authorized.",
            "payment": public_document(payment),
        }

    db.payments.update_one(
        {"_id": payment["_id"], "authorized": {"$ne": True}},
        {
            "$set": {
                "status": "AUTHORIZATION_REQUESTED",
                "hold_reason": (
                    "Awaiting smart-contract execution. "
                    "No funds have been released."
                ),
                "authorized": False,
                "updated_at": now_utc(),
            }
        },
    )

    db.shipments.update_one(
        {"_id": shipment_id},
        {"$set": {"payment_status": "AUTHORIZATION_REQUESTED"}},
    )

    updated = db.payments.find_one({"_id": payment["_id"]})

    return {
        "success": True,
        "message": (
            "Approval validated. Authorization request recorded; "
            "no funds have been released."
        ),
        "payment": public_document(updated),
    }


@mcp.tool()
def get_payment_status(shipment_id: str) -> dict:
    """Retrieve payment status without releasing funds."""

    payment = db.payments.find_one({"shipment_id": shipment_id})

    if not payment:
        return {
            "success": False,
            "message": "No payment record found for this shipment.",
        }

    return {
        "success": True,
        "payment": public_document(payment),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")