
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
contract_address = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS")
private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")

if not all([rpc_url, contract_address, private_key]):
    raise RuntimeError("Missing blockchain settings in .env")

w3 = Web3(Web3.HTTPProvider(rpc_url))

if not w3.is_connected():
    raise RuntimeError("Cannot connect to Hardhat. Is Terminal 1 running?")

artifact_path = (
    ROOT / "blockchain" / "artifacts" / "contracts"
    / "ChainFlowSettlement.sol" / "ChainFlowSettlement.json"
)

with artifact_path.open("r", encoding="utf-8") as file:
    artifact = json.load(file)

contract = w3.eth.contract(
    address=Web3.to_checksum_address(contract_address),
    abi=artifact["abi"],
)

account = w3.eth.account.from_key(private_key)
owner = contract.functions.owner().call()

print("Blockchain connection: SUCCESS")
print("Contract address:", contract.address)
print("Contract owner:", owner)
print("Configured account:", account.address)

if account.address.lower() != owner.lower():
    raise RuntimeError(
        "The configured private key does not match the contract owner."
    )

print("Deployer account matches contract owner: YES")
