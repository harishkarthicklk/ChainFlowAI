import unittest
from unittest.mock import patch

from verification import safety_gate
from coordinator.coordinator_agent import request_human_decision


REQUIRED_EVIDENCE = {
    "SUPPLIER_REPORT",
    "INVENTORY_RECORD",
    "RFID_SCAN",
    "WEIGHT_ESTIMATE",
}


class FakeCollection:
    """In-memory MongoDB substitute; does not modify real MongoDB."""

    def __init__(self, documents=None):
        self.documents = documents or []

    def find_one(self, query):
        for document in self.documents:
            if all(document.get(k) == v for k, v in query.items()):
                return document.copy()
        return None

    def update_one(self, query, update, upsert=False):
        document = None

        for item in self.documents:
            if all(item.get(k) == v for k, v in query.items()):
                document = item
                break

        if document is None and upsert:
            document = dict(query)
            self.documents.append(document)

        if document is not None:
            document.update(update.get("$set", {}))


class FakeDatabase:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def make_test_database(simulation_only=False):
    shipment_id = "SHIP-TEST-APPROVAL-001"
    report_id = "VER-TEST-APPROVAL-001"
    quantity = 100

    shipment = {
        "_id": shipment_id,
        "order_id": "ORD-TEST-001",
        "quantity_received": quantity,
    }

    report = {
        "_id": report_id,
        "shipment_id": shipment_id,
        "status": "VERIFIED",
        "simulation_only": simulation_only,
        "discrepancy_detected": False,
        "checked_at": "TEST-TIMESTAMP-001",
        "ordered_quantity": quantity,
        "received_quantity": quantity,
        "source_quantities": {
            evidence: quantity for evidence in REQUIRED_EVIDENCE
        },
        "evidence_statuses": {
            evidence: "VERIFIED" for evidence in REQUIRED_EVIDENCE
        },
        "missing_evidence_types": [],
        "missing_quantity_types": [],
        "duplicate_evidence_types": [],
        "mismatches": [],
    }

    payment = {
        "_id": "PAY-TEST-001",
        "shipment_id": shipment_id,
        "status": "ON_HOLD",
        "authorized": False,
    }

    return FakeDatabase({
        "shipments": FakeCollection([shipment]),
        "verification_reports": FakeCollection([report]),
        "manual_approvals": FakeCollection([]),
        "payments": FakeCollection([payment]),
    })


class TestManualApprovalWorkflow(unittest.TestCase):

    def setUp(self):
        self.shipment_id = "SHIP-TEST-APPROVAL-001"
        self.fake_db = make_test_database()

        self.db_patch = patch.object(
            safety_gate, "db", self.fake_db
        )
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)

    def test_yes_records_approval(self):
        result = safety_gate.record_manual_decision(
            self.shipment_id, "YES", approved_by="test-user"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "APPROVED")

        allowed, reason = safety_gate.require_transaction_approval(
            self.shipment_id
        )

        self.assertTrue(allowed, reason)

        payment = self.fake_db["payments"].find_one(
            {"shipment_id": self.shipment_id}
        )
        self.assertFalse(payment["authorized"])

    def test_no_rejects_approval(self):
        result = safety_gate.record_manual_decision(
            self.shipment_id, "NO"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "REJECTED")

        allowed, _ = safety_gate.require_transaction_approval(
            self.shipment_id
        )
        self.assertFalse(allowed)

        payment = self.fake_db["payments"].find_one(
            {"shipment_id": self.shipment_id}
        )
        self.assertEqual(payment["status"], "ON_HOLD")
        self.assertFalse(payment["authorized"])

    def test_yes_is_blocked_for_simulated_evidence(self):
        self.fake_db["verification_reports"].documents[0][
            "simulation_only"
        ] = True

        result = safety_gate.record_manual_decision(
            self.shipment_id, "YES"
        )

        self.assertFalse(result["success"])

        approval = self.fake_db["manual_approvals"].find_one(
            {"shipment_id": self.shipment_id}
        )
        self.assertIsNone(approval)

    def test_invalid_decision_is_rejected(self):
        result = safety_gate.record_manual_decision(
            self.shipment_id, "MAYBE"
        )

        self.assertFalse(result["success"])

    def test_terminal_prompt_accepts_yes(self):
        with patch(
            "builtins.input", side_effect=["MAYBE", "YES"]
        ), patch("builtins.print"):
            result = request_human_decision(self.shipment_id)

        self.assertEqual(result, "YES")

    def test_terminal_prompt_accepts_no(self):
        with patch("builtins.input", return_value="NO"):
            result = request_human_decision(self.shipment_id)

        self.assertEqual(result, "NO")


if __name__ == "__main__":
    unittest.main(verbosity=2)