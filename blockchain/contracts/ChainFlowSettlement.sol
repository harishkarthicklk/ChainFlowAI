
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ChainFlowSettlement {
    address public immutable owner;

    struct Shipment {
        uint256 orderedQuantity;
        uint256 receivedQuantity;
        uint256 amount;
        bool verificationPassed;
        bool manualApproval;
        bool rejected;
        bool settled;
        bool exists;
    }

    mapping(bytes32 => Shipment) private shipments;

    event ShipmentRegistered(
        bytes32 indexed shipmentId,
        uint256 orderedQuantity,
        uint256 amount
    );

    event VerificationRecorded(
        bytes32 indexed shipmentId,
        uint256 receivedQuantity,
        bool passed
    );

    event ManualApprovalRecorded(
        bytes32 indexed shipmentId,
        bool approved
    );

    event SettlementCompleted(
        bytes32 indexed shipmentId,
        uint256 amount,
        address indexed approvedBy
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerShipment(
        string calldata shipmentId,
        uint256 orderedQuantity,
        uint256 amount
    ) external onlyOwner {
        bytes32 id = keccak256(bytes(shipmentId));

        require(bytes(shipmentId).length > 0, "Shipment ID required");
        require(!shipments[id].exists, "Shipment already registered");
        require(orderedQuantity > 0, "Quantity must be positive");
        require(amount > 0, "Amount must be positive");

        shipments[id] = Shipment({
            orderedQuantity: orderedQuantity,
            receivedQuantity: 0,
            amount: amount,
            verificationPassed: false,
            manualApproval: false,
            rejected: false,
            settled: false,
            exists: true
        });

        emit ShipmentRegistered(id, orderedQuantity, amount);
    }

    function recordVerification(
        string calldata shipmentId,
        uint256 receivedQuantity,
        bool evidenceAuthenticated
    ) external onlyOwner {
        bytes32 id = keccak256(bytes(shipmentId));
        Shipment storage shipment = shipments[id];

        require(shipment.exists, "Shipment not registered");
        require(!shipment.settled, "Already settled");
        require(!shipment.rejected, "Shipment rejected");

        bool passed =
            evidenceAuthenticated &&
            receivedQuantity == shipment.orderedQuantity;

        shipment.receivedQuantity = receivedQuantity;
        shipment.verificationPassed = passed;
        shipment.manualApproval = false;

        emit VerificationRecorded(id, receivedQuantity, passed);
    }

    function recordManualApproval(
        string calldata shipmentId,
        bool approved
    ) external onlyOwner {
        bytes32 id = keccak256(bytes(shipmentId));
        Shipment storage shipment = shipments[id];

        require(shipment.exists, "Shipment not registered");
        require(!shipment.settled, "Already settled");
        require(!shipment.rejected, "Shipment rejected");

        require(
            shipment.verificationPassed,
            "Verification must pass first"
        );

        if (!approved) {
            shipment.rejected = true;
            shipment.manualApproval = false;
        } else {
            shipment.manualApproval = true;
        }

        emit ManualApprovalRecorded(id, approved);
    }

    function settleShipment(
        string calldata shipmentId
    ) external onlyOwner {
        bytes32 id = keccak256(bytes(shipmentId));
        Shipment storage shipment = shipments[id];

        require(shipment.exists, "Shipment not registered");
        require(!shipment.rejected, "Shipment rejected");
        require(!shipment.settled, "Already settled");
        require(shipment.verificationPassed, "Verification required");
        require(shipment.manualApproval, "Manual approval required");
        require(
            shipment.receivedQuantity == shipment.orderedQuantity,
            "Quantity mismatch"
        );

        shipment.settled = true;

        emit SettlementCompleted(
            id,
            shipment.amount,
            msg.sender
        );
    }

    function getShipment(
        string calldata shipmentId
    )
        external
        view
        returns (
            uint256 orderedQuantity,
            uint256 receivedQuantity,
            uint256 amount,
            bool verificationPassed,
            bool manualApproval,
            bool rejected,
            bool settled
        )
    {
        Shipment storage shipment =
            shipments[keccak256(bytes(shipmentId))];

        require(shipment.exists, "Shipment not registered");

        return (
            shipment.orderedQuantity,
            shipment.receivedQuantity,
            shipment.amount,
            shipment.verificationPassed,
            shipment.manualApproval,
            shipment.rejected,
            shipment.settled
        );
    }
}
