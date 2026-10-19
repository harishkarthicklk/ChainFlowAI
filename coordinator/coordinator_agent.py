
import asyncio
import json
import sys
from decimal import Decimal
from datetime import datetime, timezone

from agents.supplier_agent import SupplierAgent
from agents.inventory_agent import InventoryAgent
from agents.warehouse_agent import WarehouseAgent
from agents.logistics_agent import LogisticsAgent
from agents.finance_agent import FinanceAgent

from mcp_servers.common import db
from verification.verification_engine import verify_shipment
from verification.safety_gate import (
    evaluate_verification_gate,
    record_manual_decision,
    require_transaction_approval,
)


AGENT_CLASSES = [
    SupplierAgent,
    InventoryAgent,
    WarehouseAgent,
    LogisticsAgent,
    FinanceAgent,
]


def request_human_decision(shipment_id):
    """Request explicit YES/NO input in the terminal."""
    while True:
        decision = input(
            f"\nShipment {shipment_id} passed the safety gate.\n"
            "Approve proceeding? Enter YES or NO: "
        ).strip().upper()

        if decision in {"YES", "NO"}:
            return decision

        print("Invalid input. Please enter YES or NO.")


def force_payment_hold(shipment_id, reason):
    """Keep MongoDB payment and shipment states on hold."""
    now = datetime.now(timezone.utc)

    db["payments"].update_one(
        {"shipment_id": shipment_id},
        {
            "$set": {
                "status": "ON_HOLD",
                "authorized": False,
                "hold_reason": str(reason),
                "updated_at": now,
            }
        },
        upsert=True,
    )

    db["shipments"].update_one(
        {"_id": shipment_id},
        {
            "$set": {
                "payment_status": "ON_HOLD",
                "payment_hold_reason": str(reason),
                "updated_at": now,
            }
        },
    )


def get_contract_amount(order):
    """
    Return the order amount in whole INR rupees.
    The current Solidity contract stores an integer amount,
    without a separate currency field.
    """
    currency = str(order.get("currency", "INR")).upper()

    if currency != "INR":
        raise ValueError(
            f"Unsupported currency for this contract: {currency}"
        )

    quantity = Decimal(str(order["quantity_ordered"]))
    unit_price = Decimal(str(order["unit_price"]))

    if quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("Ordered quantity must be a positive whole number.")

    if unit_price <= 0:
        raise ValueError("Unit price must be positive.")

    amount = quantity * unit_price

    if amount != amount.to_integral_value():
        raise ValueError(
            "Order amount must be a whole number of INR rupees."
        )

    return int(quantity), int(amount)


async def run_coordinator(shipment_id):
    shipment = db["shipments"].find_one({"_id": shipment_id})

    if not shipment:
        raise ValueError(f"Shipment not found: {shipment_id}")

    order = db["orders"].find_one(
        {"_id": shipment.get("order_id")}
    )

    if not order:
        raise ValueError("Associated order was not found.")

    agents = {}
    connected_agents = []
    verification_status = "NOT_CHECKED"
    decision_message = "HOLD - verification not completed."

    print("\n" + "=" * 60)
    print("CHAINFLOW AI - COORDINATOR AGENT")
    print("=" * 60)

    try:
        # Connect the five MCP agents.
        for agent_class in AGENT_CLASSES:
            agent = agent_class()
            print(f"\n[STARTING] {agent.name}")

            await agent.connect()

            agents[agent.server_name] = agent
            connected_agents.append(agent)

        print("\n[COORDINATOR] All five agents connected.")

        if order.get("status") == "DRAFT":
            await agents["supplier"].confirm_order(order["_id"])

        order = db["orders"].find_one({"_id": order["_id"]})

        if not order or order.get("status") != "CONFIRMED":
            raise RuntimeError("Order is not confirmed. Workflow stopped.")

        await agents["inventory"].check_stock(order["product_id"])
        await agents["logistics"].get_shipment_status(shipment_id)

        # Run verification and evaluate the Python safety gate.
        print("\n[COORDINATOR] Running verification engine...")
        verification = verify_shipment(shipment_id)

        print(json.dumps(verification, indent=2, default=str))
        verification_status = verification.get("status", "UNKNOWN")

        current_shipment = db["shipments"].find_one(
            {"_id": shipment_id}
        )
        report = db["verification_reports"].find_one(
            {"shipment_id": shipment_id}
        )

        eligible, reason = evaluate_verification_gate(
            current_shipment, report
        )

        if not eligible:
            print(f"\n[SAFETY GATE BLOCKED] {reason}")

            # Place the hold first; a Finance MCP failure must not bypass it.
            force_payment_hold(shipment_id, reason)
            try:
                payable_result = await agents["finance"].calculate_payable_amount(
                    shipment_id
                )
                print("\n[FINANCE PAYABLE CALCULATION]")
                print(json.dumps(payable_result, indent=2, default=str))
            except Exception as finance_exc:
                print(f"[FINANCE WARNING] Payable calculation failed: {finance_exc}")

            if verification_status == "DISCREPANCY":
                decision_message = (
                    "TRANSACTION NOT PROCESSED - quantity discrepancy detected; "
                    f"manual approval and blockchain execution are blocked. {reason}"
                )
            else:
                decision_message = (
                    "TRANSACTION NOT PROCESSED - safety gate blocked manual approval "
                    f"and blockchain execution. {reason}"
                )

        else:
            # Lazy import: simulated/blocked shipments do not need
            # an active blockchain connection.
            from blockchain_service import (
                register_shipment,
                record_verification,
                record_manual_approval,
                settle_shipment,
                get_shipment,
            )
            from web3.exceptions import ContractLogicError

            ordered_quantity, amount = get_contract_amount(order)
            received_quantity = int(report["received_quantity"])

            if received_quantity != ordered_quantity:
                raise RuntimeError(
                    "Safety check failed: received quantity differs "
                    "from the order."
                )

            # Check whether this shipment was registered previously.
            chain_state = None

            try:
                chain_state = get_shipment(shipment_id)
            except ContractLogicError:
                # An unregistered shipment can revert on getShipment().
                # If another contract error caused this, registration will fail
                # safely rather than allowing settlement to continue.
                chain_state = None

            if chain_state is None:
                registration = register_shipment(
                    shipment_id,
                    ordered_quantity,
                    amount,
                )
                print("\n[BLOCKCHAIN REGISTRATION]")
                print(json.dumps(registration, indent=2))
                chain_state = get_shipment(shipment_id)

            # Never reuse a contract record with different order data.
            if (
                chain_state["ordered_quantity"] != ordered_quantity
                or chain_state["amount"] != amount
            ):
                raise RuntimeError(
                    "Blockchain shipment data does not match MongoDB. "
                    "Execution stopped."
                )

            if chain_state["settled"]:
                decision_message = (
                    "HOLD - this shipment is already settled on-chain; "
                    "no duplicate settlement was attempted."
                )

            elif chain_state["rejected"]:
                decision_message = (
                    "STOP - this shipment was previously rejected "
                    "on-chain."
                )

            else:
                # Do not reset an existing valid verification, because
                # recordVerification resets the contract's manual approval.
                if not (
                    chain_state["verification_passed"]
                    and chain_state["received_quantity"]
                    == received_quantity
                ):
                    verification_tx = record_verification(
                        shipment_id,
                        received_quantity,
                        True,
                    )
                    print("\n[BLOCKCHAIN VERIFICATION]")
                    print(json.dumps(verification_tx, indent=2))

                # This flag means the Python safety gate passed.
                # It is NOT cryptographic proof of physical evidence.
                manual_decision = request_human_decision(shipment_id)

                approval_result = record_manual_decision(
                    shipment_id,
                    manual_decision,
                    approved_by="human",
                )

                print("\n[MONGODB MANUAL APPROVAL]")
                print(json.dumps(approval_result, indent=2, default=str))

                if not approval_result.get("success"):
                    force_payment_hold(
                        shipment_id,
                        approval_result.get(
                            "message", "Manual approval failed."
                        ),
                    )
                    decision_message = (
                        "HOLD - MongoDB rejected the manual decision."
                    )

                elif manual_decision == "NO":
                    # Record rejection on-chain. If it fails, MongoDB
                    # still keeps the payment on hold.
                    try:
                        rejection_tx = record_manual_approval(
                            shipment_id, False
                        )
                        print("\n[BLOCKCHAIN REJECTION]")
                        print(json.dumps(rejection_tx, indent=2))
                        decision_message = (
                            "STOP - manually rejected; settlement blocked."
                        )
                    except Exception as exc:
                        force_payment_hold(shipment_id, str(exc))
                        decision_message = (
                            "STOP - MongoDB rejection recorded, but "
                            f"blockchain rejection failed: {exc}"
                        )

                else:
                    try:
                        # Recheck MongoDB verification and approval.
                        approval_ok, approval_reason = (
                            require_transaction_approval(shipment_id)
                        )

                        if not approval_ok:
                            raise RuntimeError(approval_reason)

                        approval_tx = record_manual_approval(
                            shipment_id, True
                        )
                        print("\n[BLOCKCHAIN APPROVAL]")
                        print(json.dumps(approval_tx, indent=2))

                        # Finance requests authorization; it does not
                        # transfer money.
                        await agents["finance"].calculate_payable_amount(
                            shipment_id
                        )

                        auth_result = await agents[
                            "finance"
                        ].request_payment_authorization(shipment_id)

                        print("\n[FINANCE AUTHORIZATION REQUEST]")
                        print(
                            json.dumps(
                                auth_result, indent=2, default=str
                            )
                        )

                        if not auth_result.get("success"):
                            force_payment_hold(
                                shipment_id,
                                "Finance authorization request failed.",
                            )
                            decision_message = (
                                "HOLD - Finance authorization request failed."
                            )
                        else:
                            # Final on-chain state change occurs only after
                            # the gate, human approval, and Finance request.
                            settlement_tx = settle_shipment(shipment_id)
                            print("\n[BLOCKCHAIN SETTLEMENT]")
                            print(
                                json.dumps(settlement_tx, indent=2)
                            )
                            decision_message = (
                                "SUCCESS - settlement state recorded "
                                "on-chain. No money was transferred."
                            )

                    except Exception as exc:
                        force_payment_hold(shipment_id, str(exc))
                        decision_message = (
                            "HOLD - transaction workflow failed: "
                            f"{exc}"
                        )

        # Always try to ask Finance for the latest payment status, but do not
        # let a reporting-only MCP error hide the coordinator's final report.
        try:
            payment_status_result = await agents["finance"].get_payment_status(
                shipment_id
            )
            print("\n[FINANCE PAYMENT STATUS]")
            print(json.dumps(payment_status_result, indent=2, default=str))
        except Exception as finance_exc:
            print(f"[FINANCE WARNING] Could not fetch latest payment status: {finance_exc}")

        final_shipment = db["shipments"].find_one(
            {"_id": shipment_id}
        )
        payment = db["payments"].find_one(
            {"shipment_id": shipment_id}
        )
        approval = db["manual_approvals"].find_one(
            {"shipment_id": shipment_id}
        )

        print("\n" + "=" * 60)
        print("FINAL COORDINATOR REPORT")
        print("=" * 60)
        print(f"Shipment       : {shipment_id}")
        print(f"Order          : {order['_id']}")
        print(f"Verification   : {verification_status}")
        print(
            "Manual decision: "
            f"{approval.get('decision') if approval else 'NOT AVAILABLE'}"
        )
        print(
            "Approval status: "
            f"{approval.get('status') if approval else 'NOT APPROVED'}"
        )
        print(f"Tracking       : {final_shipment.get('tracking_status')}")
        print(
            "Payment status : "
            f"{payment.get('status') if payment else 'NOT FOUND'}"
        )
        print(
            "Authorized     : "
            f"{payment.get('authorized') if payment else False}"
        )
        print(f"Decision       : {decision_message}")
        if verification_status == "MATCHED_SIMULATED":
            print("Mode           : DEMO ONLY (simulated evidence; not production verification)")
        if decision_message.startswith("SUCCESS"):
            print("Transaction    : PROCESSED ON LOCAL BLOCKCHAIN (no money transferred)")
        elif "manual_decision" in locals() and manual_decision == "NO":
            print("Transaction    : NOT PROCESSED (manual rejection)")
        else:
            print("Transaction    : NOT PROCESSED")
        print("=" * 60)

    except Exception as exc:
        # Fail closed on unexpected workflow errors. Do not continue to
        # another transaction after an exception.
        try:
            force_payment_hold(shipment_id, f"Coordinator error: {exc}")
        except Exception as hold_exc:
            print(f"[CRITICAL] Could not record payment hold: {hold_exc}")

        print("\n[COORDINATOR ERROR] Workflow stopped safely.")
        print(f"Reason: {exc}")
        print("Payment must remain ON_HOLD; no success is reported.")

        raise

    finally:
        for agent in reversed(connected_agents):
            try:
                await agent.close()
            except Exception as exc:
                print(f"[CLEANUP WARNING] {agent.name}: {exc}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python -m coordinator.coordinator_agent <shipment_id>"
        )
        sys.exit(2)

    try:
        asyncio.run(run_coordinator(sys.argv[1]))
    except Exception as exc:
        print(f"\n[COORDINATOR ERROR] {exc}")
        sys.exit(1)
