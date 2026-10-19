
from uuid import uuid4

from blockchain_service import (
    register_shipment,
    record_verification,
    record_manual_approval,
    settle_shipment,
    get_shipment,
)

PREFIX = f"TEST-{uuid4().hex[:8].upper()}"


def expect_blocked(action, description):
    try:
        action()
    except Exception as exc:
        print(f"PASS: {description} was blocked ({type(exc).__name__})")
        return

    raise AssertionError(f"FAIL: {description} was unexpectedly allowed")


def register(shipment_id, quantity=100, amount=50000):
    result = register_shipment(shipment_id, quantity, amount)
    print(f"Registered {shipment_id}: {result['status']}")


def test_yes_approval():
    shipment_id = f"{PREFIX}-YES"

    register(shipment_id)
    record_verification(shipment_id, 100, True)
    record_manual_approval(shipment_id, True)
    settle_shipment(shipment_id)

    state = get_shipment(shipment_id)

    assert state["verification_passed"] is True
    assert state["manual_approval"] is True
    assert state["settled"] is True

    print("PASS: Verified shipment with YES approval was settled.")


def test_no_approval():
    shipment_id = f"{PREFIX}-NO"

    register(shipment_id)
    record_verification(shipment_id, 100, True)
    record_manual_approval(shipment_id, False)

    state = get_shipment(shipment_id)
    assert state["rejected"] is True

    expect_blocked(
        lambda: settle_shipment(shipment_id),
        "Settlement after NO approval",
    )

    print("PASS: NO approval rejected the shipment.")


def test_quantity_mismatch():
    shipment_id = f"{PREFIX}-MISMATCH"

    register(shipment_id, quantity=100)
    record_verification(shipment_id, 90, True)

    state = get_shipment(shipment_id)

    assert state["verification_passed"] is False
    assert state["received_quantity"] == 90

    expect_blocked(
        lambda: record_manual_approval(shipment_id, True),
        "Approval of a quantity-mismatched shipment",
    )

    expect_blocked(
        lambda: settle_shipment(shipment_id),
        "Settlement of a quantity-mismatched shipment",
    )

    print("PASS: Quantity mismatch prevented approval and settlement.")


if __name__ == "__main__":
    print("Running isolated local blockchain tests...")
    print(f"Test prefix: {PREFIX}")

    test_yes_approval()
    test_no_approval()
    test_quantity_mismatch()

    print("\nALL THREE BLOCKCHAIN SCENARIOS PASSED.")
