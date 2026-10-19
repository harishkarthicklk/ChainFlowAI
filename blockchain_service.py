
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

RPC_URL = os.getenv("BLOCKCHAIN_RPC_URL")
CONTRACT_ADDRESS = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY")

if not all([RPC_URL, CONTRACT_ADDRESS, PRIVATE_KEY]):
    raise RuntimeError("Missing blockchain configuration in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Cannot connect to the Hardhat blockchain")

artifact_path = (
    ROOT / "blockchain" / "artifacts" / "contracts"
    / "ChainFlowSettlement.sol" / "ChainFlowSettlement.json"
)

with artifact_path.open("r", encoding="utf-8") as file:
    artifact = json.load(file)

account = w3.eth.account.from_key(PRIVATE_KEY)

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=artifact["abi"],
)

owner = contract.functions.owner().call()

if account.address.lower() != owner.lower():
    raise RuntimeError("Configured account is not the contract owner")


def _send_transaction(function):
    """Sign, submit, and confirm a contract transaction."""
    nonce = w3.eth.get_transaction_count(account.address)

    tx = function.build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gas": 1_000_000,
        "gasPrice": w3.eth.gas_price,
    })

    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError(f"Blockchain transaction failed: {tx_hash.hex()}")

    return {
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "status": "CONFIRMED",
    }


def register_shipment(shipment_id, ordered_quantity, amount):
    return _send_transaction(
        contract.functions.registerShipment(
            shipment_id, int(ordered_quantity), int(amount)
        )
    )


def record_verification(
    shipment_id, received_quantity, evidence_authenticated
):
    return _send_transaction(
        contract.functions.recordVerification(
            shipment_id,
            int(received_quantity),
            bool(evidence_authenticated),
        )
    )


def record_manual_approval(shipment_id, approved):
    return _send_transaction(
        contract.functions.recordManualApproval(
            shipment_id, bool(approved)
        )
    )


def settle_shipment(shipment_id):
    return _send_transaction(
        contract.functions.settleShipment(shipment_id)
    )


def get_shipment(shipment_id):
    result = contract.functions.getShipment(shipment_id).call()

    return {
        "ordered_quantity": result[0],
        "received_quantity": result[1],
        "amount": result[2],
        "verification_passed": result[3],
        "manual_approval": result[4],
        "rejected": result[5],
        "settled": result[6],
    }


if __name__ == "__main__":
    print("Blockchain service: CONNECTED")
    print("Contract:", contract.address)
    print("Owner:", owner)
    print("Chain ID:", w3.eth.chain_id)
