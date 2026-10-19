
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp_servers.common import db, public_document

mcp = FastMCP("ChainFlow Warehouse Verification Server")


def now_utc():
    return datetime.now(timezone.utc)


def find_shipment(shipment_id):
    return db.shipments.find_one({"_id": shipment_id})


def save_evidence(
    shipment,
    source_type,
    quantity,
    evidence_id,
    source_id
):
    document = {
        "_id": evidence_id,
        "shipment_id": shipment["_id"],
        "order_id": shipment["order_id"],
        "source_type": source_type,
        "reported_quantity": quantity,
        "evidence_status": "SIMULATED",
        "evidence_id": source_id,
        "observed_at": now_utc()
    }

    db.physical_evidence.update_one(
        {"_id": evidence_id},
        {"$set": document},
        upsert=True
    )

    return document


@mcp.tool()
def record_scan_count(
    shipment_id: str,
    scanned_quantity: int
) -> dict:
    """Record simulated RFID scan evidence for a shipment."""

    if scanned_quantity < 0:
        return {"success": False, "message": "Quantity cannot be negative."}

    shipment = find_shipment(shipment_id)
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    evidence = save_evidence(
        shipment,
        "RFID_SCAN",
        scanned_quantity,
        f"EVD-RFID-{shipment_id}",
        f"SRC-RFID-{shipment_id}"
    )

    return {
        "success": True,
        "message": "RFID evidence recorded; verification is not yet approved.",
        "evidence": public_document(evidence)
    }


@mcp.tool()
def record_weight_measurement(
    shipment_id: str,
    estimated_quantity: int
) -> dict:
    """Record a simulated quantity estimate derived from shipment weight."""

    if estimated_quantity < 0:
        return {"success": False, "message": "Quantity cannot be negative."}

    shipment = find_shipment(shipment_id)
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    evidence = save_evidence(
        shipment,
        "WEIGHT_ESTIMATE",
        estimated_quantity,
        f"EVD-WEIGHT-{shipment_id}",
        f"SRC-WEIGHT-{shipment_id}"
    )

    return {
        "success": True,
        "message": "Weight estimate recorded; verification is not yet approved.",
        "evidence": public_document(evidence)
    }


@mcp.tool()
def submit_receipt_evidence(
    shipment_id: str,
    received_quantity: int
) -> dict:
    """Record a warehouse receipt. This does not approve the shipment."""

    if received_quantity < 0:
        return {"success": False, "message": "Quantity cannot be negative."}

    shipment = find_shipment(shipment_id)
    if not shipment:
        return {"success": False, "message": "Shipment not found."}

    evidence = save_evidence(
        shipment,
        "WAREHOUSE_RECEIPT",
        received_quantity,
        f"EVD-RECEIPT-{shipment_id}",
        f"SRC-RECEIPT-{shipment_id}"
    )

    db.shipments.update_one(
        {"_id": shipment_id},
        {
            "$set": {
                "quantity_received": received_quantity,
                "updated_at": now_utc()
            }
        }
    )

    return {
        "success": True,
        "message": (
            "Receipt recorded. The verification engine must check "
            "the evidence before approving this shipment."
        ),
        "evidence": public_document(evidence),
        "verification_status": shipment.get("verification_status", "PENDING")
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
