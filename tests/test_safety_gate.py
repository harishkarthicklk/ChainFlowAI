import unittest

from verification.safety_gate import (
    evaluate_verification_gate,
    REQUIRED_EVIDENCE,
)


def make_shipment():
    return {
        "_id": "SHIP-TEST-001",
        "quantity_claimed": 10,
        "quantity_received": 10,
    }


def make_report():
    return {
        "_id": "VER-SHIP-TEST-001",
        "shipment_id": "SHIP-TEST-001",
        "checked_at": "test-time",
        "status": "VERIFIED",
        "simulation_only": False,
        "discrepancy_detected": False,
        "ordered_quantity": 10,
        "received_quantity": 10,
        "missing_evidence_types": [],
        "missing_quantity_types": [],
        "duplicate_evidence_types": [],
        "mismatches": [],
        "evidence_statuses": {
            key: "AUTHENTICATED" for key in REQUIRED_EVIDENCE
        },
        "source_quantities": {
            key: 10 for key in REQUIRED_EVIDENCE
        },
    }


class TestSafetyGate(unittest.TestCase):

    def test_fully_verified_shipment_passes(self):
        allowed, _ = evaluate_verification_gate(
            make_shipment(), make_report()
        )
        self.assertTrue(allowed)

    def test_discrepancy_is_blocked(self):
        report = make_report()
        report["status"] = "DISCREPANCY"
        report["discrepancy_detected"] = True

        allowed, _ = evaluate_verification_gate(
            make_shipment(), report
        )
        self.assertFalse(allowed)

    def test_simulated_evidence_is_blocked(self):
        report = make_report()
        report["status"] = "MATCHED_SIMULATED"
        report["simulation_only"] = True

        allowed, _ = evaluate_verification_gate(
            make_shipment(), report
        )
        self.assertFalse(allowed)

    def test_untrusted_evidence_is_blocked(self):
        report = make_report()
        report["evidence_statuses"]["RFID_SCAN"] = "UNSPECIFIED"

        allowed, _ = evaluate_verification_gate(
            make_shipment(), report
        )
        self.assertFalse(allowed)

    def test_missing_evidence_is_blocked(self):
        report = make_report()
        report["missing_evidence_types"] = ["RFID_SCAN"]

        allowed, _ = evaluate_verification_gate(
            make_shipment(), report
        )
        self.assertFalse(allowed)

    def test_quantity_mismatch_is_blocked(self):
        report = make_report()
        report["source_quantities"]["RFID_SCAN"] = 9

        allowed, _ = evaluate_verification_gate(
            make_shipment(), report
        )
        self.assertFalse(allowed)

    def test_missing_received_quantity_is_blocked(self):
        shipment = make_shipment()
        shipment["quantity_received"] = None

        allowed, _ = evaluate_verification_gate(
            shipment, make_report()
        )
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)