
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { network } from "hardhat";

describe("ChainFlowSettlement", function () {
  async function deployFixture() {
    const { viem } = await network.connect();

    const contract = await viem.deployContract("ChainFlowSettlement");

    return { viem, contract };
  }

  it("registers a shipment and starts unverified", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-001", 100n, 500000n]);

    const shipment = await contract.read.getShipment(["SHIP-TEST-001"]);

    assert.equal(shipment[0], 100n);
    assert.equal(shipment[3], false);
    assert.equal(shipment[4], false);
    assert.equal(shipment[6], false);
  });

  it("blocks settlement before verification", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-002", 100n, 500000n]);

    await assert.rejects(
      contract.write.settleShipment(["SHIP-TEST-002"])
    );
  });

  it("blocks a quantity mismatch", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-003", 100n, 500000n]);

    await contract.write.recordVerification([
      "SHIP-TEST-003",
      95n,
      true
    ]);

    const shipment = await contract.read.getShipment(["SHIP-TEST-003"]);

    assert.equal(shipment[3], false);

    await assert.rejects(
      contract.write.recordManualApproval(["SHIP-TEST-003", true])
    );
  });

  it("allows settlement after verification and YES approval", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-004", 100n, 500000n]);

    await contract.write.recordVerification([
      "SHIP-TEST-004",
      100n,
      true
    ]);

    await contract.write.recordManualApproval(["SHIP-TEST-004", true]);

    await contract.write.settleShipment(["SHIP-TEST-004"]);

    const shipment = await contract.read.getShipment(["SHIP-TEST-004"]);

    assert.equal(shipment[3], true);
    assert.equal(shipment[4], true);
    assert.equal(shipment[6], true);
  });

  it("blocks settlement after NO approval", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-005", 100n, 500000n]);

    await contract.write.recordVerification([
      "SHIP-TEST-005",
      100n,
      true
    ]);

    await contract.write.recordManualApproval(["SHIP-TEST-005", false]);

    const shipment = await contract.read.getShipment(["SHIP-TEST-005"]);

    assert.equal(shipment[5], true);

    await assert.rejects(
      contract.write.settleShipment(["SHIP-TEST-005"])
    );
  });

  it("prevents duplicate shipment registration", async function () {
    const { contract } = await deployFixture();

    await contract.write.registerShipment(["SHIP-TEST-006", 100n, 500000n]);

    await assert.rejects(
      contract.write.registerShipment(["SHIP-TEST-006", 100n, 500000n])
    );
  });
});
