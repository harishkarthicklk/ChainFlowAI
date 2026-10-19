# tests/test_verification_engine.py

from mcp_servers.common import db
from verification.verification_engine import verify_shipment


def test_battery_shipment_detects_discrepancy():
    shipment_id = "SHIP-2026-0001"

    result = verify_shipment(shipment_id)

    print("\nBATTERY RESULT:")
    print(result)

    assert result["status"] == "DISCREPANCY", result
    assert result["discrepancy_detected"] is True

    # The sample data should show 150 fewer units in RFID and weight.
    assert any(
        mismatch["source"] == "RFID_SCAN"
        and mismatch["difference"] == -150
        for mismatch in result["mismatches"]
    ), result

    shipment = db["shipments"].find_one({"_id": shipment_id})
    assert shipment["verification_status"] == "DISCREPANCY"

    payment = db["payments"].find_one({"shipment_id": shipment_id})
    if payment:
        assert payment.get("status") == "ON_HOLD"
        assert payment.get("authorized") is False


def test_display_shipment_matches_but_is_simulated():
    shipment_id = "SHIP-2026-0002"

    result = verify_shipment(shipment_id)

    print("\nDISPLAY RESULT:")
    print(result)

    assert result["status"] == "MATCHED_SIMULATED", result
    assert result["discrepancy_detected"] is False
    assert result["simulation_only"] is True

    shipment = db["shipments"].find_one({"_id": shipment_id})
    assert shipment["verification_status"] == "MATCHED_SIMULATED"

    payment = db["payments"].find_one({"shipment_id": shipment_id})
    if payment:
        assert payment.get("status") == "ON_HOLD"
        assert payment.get("authorized") is False


if __name__ == "__main__":
    test_battery_shipment_detects_discrepancy()
    test_display_shipment_matches_but_is_simulated()
    print("\nAll Phase 3 verification tests passed.")