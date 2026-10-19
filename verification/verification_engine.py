# verification/verification_engine.py

from datetime import datetime, timezone
from mcp_servers.common import db

REQUIRED_EVIDENCE_TYPES = {
    "SUPPLIER_REPORT",
    "INVENTORY_RECORD",
    "RFID_SCAN",
    "WEIGHT_ESTIMATE",
}

# These labels alone do not prove authenticity; they are accepted here
# only as upstream trust labels for this phase.
TRUSTED_STATUSES = {"VERIFIED", "AUTHENTICATED", "TRUSTED", "VALIDATED"}


def utc_now():
    return datetime.now(timezone.utc)


def get_value(document, *keys):
    """Return the first non-None value found among possible field names."""
    for key in keys:
        if document.get(key) is not None:
            return document[key]
    return None


def normalize_type(evidence):
    value = get_value(evidence, "evidence_type", "source_type", "type")
    return str(value or "").strip().upper()


def normalize_quantity(evidence):
    value = get_value(
        evidence,
        "quantity",
        "reported_quantity",
        "scanned_quantity",
        "estimated_quantity",
        "quantity_received",
    )
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def is_explicitly_simulated(value):
    """Recognize boolean and common text representations of simulation flags."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "simulated"}
    return False


def verify_shipment(shipment_id):
    shipments = db["shipments"]
    orders = db["orders"]
    evidence_collection = db["physical_evidence"]
    payments = db["payments"]
    reports = db["verification_reports"]

    shipment = shipments.find_one({"_id": shipment_id})
    if not shipment:
        return {
            "shipment_id": shipment_id,
            "status": "SHIPMENT_NOT_FOUND",
            "message": "No shipment exists with this ID.",
        }

    order_id = shipment.get("order_id")
    order = orders.find_one({"_id": order_id})

    if not order:
        result = {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "status": "INCOMPLETE_EVIDENCE",
            "reason": "The related order was not found.",
            "simulation_only": True,
            "checked_at": utc_now(),
        }
        shipments.update_one(
            {"_id": shipment_id},
            {"$set": {"verification_status": "INCOMPLETE_EVIDENCE"}},
        )
        reports.update_one(
            {"_id": f"VER-{shipment_id}"},
            {"$set": result},
            upsert=True,
        )
        return result

    ordered_quantity = get_value(order, "quantity_ordered", "quantity")
    try:
        ordered_quantity = float(ordered_quantity)
    except (TypeError, ValueError):
        ordered_quantity = None

    evidence_docs = list(
        evidence_collection.find({"shipment_id": shipment_id})
    )

    evidence_by_type = {}
    duplicate_types = set()

    for evidence in evidence_docs:
        evidence_type = normalize_type(evidence)
        if not evidence_type:
            continue
        if evidence_type in evidence_by_type:
            duplicate_types.add(evidence_type)
        else:
            evidence_by_type[evidence_type] = evidence

    missing_types = sorted(
        REQUIRED_EVIDENCE_TYPES - set(evidence_by_type.keys())
    )

    source_quantities = {}
    evidence_statuses = {}
    # Simulation flags are explicit safety signals. Trusted status labels
    # must not override a record marked as simulated.
    simulation_only = is_explicitly_simulated(
        shipment.get("simulation_only", False)
    )
    mismatches = []

    for evidence_type, evidence in evidence_by_type.items():
        quantity = normalize_quantity(evidence)
        evidence_status = str(evidence.get("status", "")).strip().upper()

        source_quantities[evidence_type] = quantity
        evidence_statuses[evidence_type] = evidence_status or "UNSPECIFIED"

        if (
            evidence_status not in TRUSTED_STATUSES
            or is_explicitly_simulated(evidence.get("simulation_only", False))
            or is_explicitly_simulated(evidence.get("simulated", False))
        ):
            simulation_only = True

        if (
            evidence_type in REQUIRED_EVIDENCE_TYPES
            and quantity is not None
            and ordered_quantity is not None
            and quantity != ordered_quantity
        ):
            mismatches.append({
                "source": evidence_type,
                "expected_quantity": ordered_quantity,
                "observed_quantity": quantity,
                "difference": quantity - ordered_quantity,
            })

    received_quantity = shipment.get("quantity_received")
    try:
        received_quantity = (
            float(received_quantity)
            if received_quantity is not None
            else None
        )
    except (TypeError, ValueError):
        received_quantity = None

    if (
        received_quantity is not None
        and ordered_quantity is not None
        and received_quantity != ordered_quantity
    ):
        mismatches.append({
            "source": "WAREHOUSE_RECEIPT",
            "expected_quantity": ordered_quantity,
            "observed_quantity": received_quantity,
            "difference": received_quantity - ordered_quantity,
        })

    missing_quantities = sorted(
        evidence_type
        for evidence_type in REQUIRED_EVIDENCE_TYPES
        if evidence_type in evidence_by_type
        and source_quantities.get(evidence_type) is None
    )

    if (
        ordered_quantity is None
        or missing_types
        or missing_quantities
        or duplicate_types
        or received_quantity is None
    ):
        status = "INCOMPLETE_EVIDENCE"
        reason = "Required evidence or the warehouse receipt is missing, ambiguous, or invalid."
        if ordered_quantity is None:
            reason = "The order quantity is missing or invalid."
        elif received_quantity is None:
            reason = "The received quantity is missing or invalid."
    elif mismatches:
        status = "DISCREPANCY"
        reason = "One or more reported quantities do not match the ordered quantity."
    elif simulation_only:
        status = "MATCHED_SIMULATED"
        reason = "Quantities match, but the evidence is not independently authenticated."
    else:
        status = "VERIFIED"
        reason = "Required evidence quantities match and carry trusted status labels."

    result = {
        "_id": f"VER-{shipment_id}",
        "shipment_id": shipment_id,
        "order_id": order_id,
        "ordered_quantity": ordered_quantity,
        "received_quantity": received_quantity,
        "source_quantities": source_quantities,
        "evidence_statuses": evidence_statuses,
        "missing_evidence_types": missing_types,
        "missing_quantity_types": missing_quantities,
        "duplicate_evidence_types": sorted(duplicate_types),
        "mismatches": mismatches,
        "discrepancy_detected": bool(mismatches),
        "status": status,
        "reason": reason,
        "simulation_only": simulation_only,
        "checked_at": utc_now(),
    }

    # Update shipment verification state.
    shipments.update_one(
        {"_id": shipment_id},
        {
            "$set": {
                "verification_status": status,
                "verification_reason": reason,
                "verification_checked_at": result["checked_at"],
            }
        },
    )

    # Never release or authorize payment in the verification engine.
    payment = payments.find_one({"shipment_id": shipment_id})
    if payment:
        payments.update_one(
            {"_id": payment["_id"]},
            {
                "$set": {
                    "status": "ON_HOLD",
                    "authorized": False,
                    "hold_reason": reason,
                    "verification_status": status,
                }
            },
        )

    report_id = result["_id"]

    report_document = {
        key: value
        for key, value in result.items()
        if key != "_id"
    }

    reports.update_one(
        {"_id": report_id},
        {"$set": report_document},
        upsert=True,
    )

    return result


if __name__ == "__main__":
    import json
    import sys

    shipment_ids = sys.argv[1:] or [
        "SHIP-2026-0001",
        "SHIP-2026-0002",
    ]

    for shipment_id in shipment_ids:
        print(f"\n--- Verification: {shipment_id} ---")
        result = verify_shipment(shipment_id)
        print(json.dumps(result, indent=2, default=str))