import os
from pathlib import Path
from datetime import datetime, timezone

from mcp_servers.common import db


def _load_project_demo_setting():
    """
    Read the demo flag from the project-root .env as well as the process
    environment. This matters because Finance runs as a separate MCP process.
    An explicit process environment variable takes precedence over .env.
    """
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if not env_file.is_file():
        return

    for raw_line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "CHAINFLOW_DEMO_ALLOW_SIMULATED_EVIDENCE":
            continue
        value = value.strip().strip("\\\"").strip("'")
        os.environ.setdefault(key.strip(), value)


_load_project_demo_setting()

# Explicit opt-in for local demonstrations only. Default remains disabled.
DEMO_ALLOW_SIMULATED_EVIDENCE = (
    os.getenv("CHAINFLOW_DEMO_ALLOW_SIMULATED_EVIDENCE", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)


TRUSTED_STATUSES = {
    "VERIFIED",
    "AUTHENTICATED",
    "TRUSTED",
    "VALIDATED",
}

REQUIRED_EVIDENCE = {
    "SUPPLIER_REPORT",
    "INVENTORY_RECORD",
    "RFID_SCAN",
    "WEIGHT_ESTIMATE",
}


def evaluate_verification_gate(shipment, report):
    if not shipment or not report:
        return False, "Shipment or verification report is missing."

    if report.get("shipment_id") != shipment.get("_id"):
        return False, "Verification report does not match the shipment."

    report_status = str(report.get("status", "")).strip().upper()
    simulation_value = report.get("simulation_only")
    simulation_is_true = (
        simulation_value is True
        or str(simulation_value).strip().lower() in {"1", "true", "yes"}
    )

    demo_simulated_match = (
        DEMO_ALLOW_SIMULATED_EVIDENCE
        and report_status == "MATCHED_SIMULATED"
        and simulation_is_true
    )

    # Report a quantity discrepancy explicitly before the generic status check.
    if report.get("discrepancy_detected") is not False or report.get("mismatches"):
        return False, "A shipment quantity discrepancy was detected."

    if report_status != "VERIFIED" and not demo_simulated_match:
        return False, "Shipment is not fully verified."

    if simulation_value is not False and str(simulation_value).strip().lower() not in {"0", "false", "no"} and not demo_simulated_match:
        return False, "Simulated evidence cannot authorize a transaction."

    if not report.get("checked_at"):
        return False, "Verification timestamp is missing."

    for field in (
        "missing_evidence_types",
        "missing_quantity_types",
        "duplicate_evidence_types",
        "mismatches",
    ):
        if report.get(field):
            return False, f"Verification failed: {field} is not empty."

    statuses = report.get("evidence_statuses") or {}
    quantities = report.get("source_quantities") or {}

    if not REQUIRED_EVIDENCE.issubset(statuses):
        return False, "Required evidence statuses are missing."

    if not REQUIRED_EVIDENCE.issubset(quantities):
        return False, "Required evidence quantities are missing."

    # In demo mode only, matching simulated evidence may reach the human prompt.
    # This is not proof of authenticity and must never be enabled in production.
    if not demo_simulated_match:
        for evidence_type in REQUIRED_EVIDENCE:
            if str(statuses[evidence_type]).strip().upper() not in TRUSTED_STATUSES:
                return False, f"{evidence_type} is not authenticated."

    try:
        ordered = float(report["ordered_quantity"])
        received = float(report["received_quantity"])
        shipment_received = float(shipment["quantity_received"])

        if ordered <= 0 or received != ordered:
            return False, "Received quantity does not match the order."

        if shipment_received != ordered:
            return False, "Shipment quantity does not match the order."

        for evidence_type in REQUIRED_EVIDENCE:
            if float(quantities[evidence_type]) != ordered:
                return False, (
                    f"{evidence_type} quantity does not match the order."
                )

    except (KeyError, TypeError, ValueError):
        return False, "A required quantity is missing or invalid."

    if demo_simulated_match:
        return (
            True,
            "DEMO MODE: quantities match, but evidence is simulated. "
            "Manual approval may be requested for local blockchain demonstration only.",
        )

    return True, "Verification passed. Manual approval may be requested."


def record_manual_decision(shipment_id, decision, approved_by="human"):
    decision = str(decision).strip().upper()

    if decision not in {"YES", "NO"}:
        return {
            "success": False,
            "message": "Enter YES or NO.",
        }

    shipment = db["shipments"].find_one({"_id": shipment_id})
    report = db["verification_reports"].find_one(
        {"shipment_id": shipment_id}
    )

    if not shipment or not report:
        return {
            "success": False,
            "message": "Shipment or verification report not found.",
        }

    eligible, reason = evaluate_verification_gate(shipment, report)

    # Never accept YES unless the safety gate passes.
    if decision == "YES" and not eligible:
        return {
            "success": False,
            "decision": "REJECTED",
            "message": f"Approval blocked: {reason}",
        }

    approval_status = "APPROVED" if decision == "YES" else "REJECTED"

    approval = {
        "shipment_id": shipment_id,
        "verification_report_id": str(report["_id"]),
        "verification_checked_at": str(report["checked_at"]),
        "status": approval_status,
        "approved_by": approved_by,
        "decision": decision,
        "reason": (
            "Human approved the transaction."
            if decision == "YES"
            else "Human rejected the transaction."
        ),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    db["manual_approvals"].update_one(
        {"shipment_id": shipment_id},
        {"$set": approval},
        upsert=True,
    )

    if decision == "NO":
        db["payments"].update_one(
            {"shipment_id": shipment_id},
            {
                "$set": {
                    "status": "ON_HOLD",
                    "authorized": False,
                    "hold_reason": "Manual approval was rejected.",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        db["shipments"].update_one(
            {"_id": shipment_id},
            {"$set": {"payment_status": "ON_HOLD"}},
        )

    return {
        "success": True,
        "shipment_id": shipment_id,
        "decision": decision,
        "status": approval_status,
        "message": approval["reason"],
    }


def require_transaction_approval(shipment_id):
    """Final safety check used by the Finance MCP server."""

    shipment = db["shipments"].find_one({"_id": shipment_id})
    report = db["verification_reports"].find_one(
        {"shipment_id": shipment_id}
    )
    approval = db["manual_approvals"].find_one(
        {"shipment_id": shipment_id}
    )

    eligible, reason = evaluate_verification_gate(shipment, report)

    if not eligible:
        return False, reason

    if not approval or approval.get("status") != "APPROVED":
        return False, "No valid human approval is recorded."

    if approval.get("verification_report_id") != str(report["_id"]):
        return False, "Approval does not match the verification report."

    if approval.get("verification_checked_at") != str(
        report.get("checked_at")
    ):
        return False, "Verification changed; fresh human approval is required."

    return True, "Verification and manual approval passed."