
import { network } from "hardhat";

const { viem, networkName } = await network.create();

console.log(`Deploying ChainFlowSettlement to ${networkName}...`);

const contract = await viem.deployContract("ChainFlowSettlement");

console.log("Deployment successful!");
console.log("Contract address:", contract.address);
