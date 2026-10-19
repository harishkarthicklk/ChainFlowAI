
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

# Load configuration
load_dotenv()

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017/"
)
DATABASE_NAME = os.getenv(
    "MONGODB_DATABASE",
    "chainflow_ai"
)

# Connect to MongoDB
client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")
db = client[DATABASE_NAME]

now = datetime.now(timezone.utc)

# --------------------------------------------------
# 1. PRODUCTS
# --------------------------------------------------
products = [
    {
        "_id": "BATTERY-001",
        "product_name": "Lithium-ion Battery",
        "category": "Battery",
        "unit": "pieces",
        "unit_weight_kg": 1.0,
        "description": "Battery units for electronic devices",
        "active": True,
        "created_at": now
    }
]

# --------------------------------------------------
# 2. INVENTORY
# --------------------------------------------------
inventory = [
    {
        "_id": "INV-BATTERY-001",
        "product_id": "BATTERY-001",
        "supplier_id": "SUPPLIER-001",
        "warehouse_id": "WAREHOUSE-001",
        "quantity_on_hand": 100000,
        "quantity_reserved": 0,
        "quantity_available": 100000,
        "updated_at": now
    }
]

# --------------------------------------------------
# 3. ORDERS
# --------------------------------------------------
orders = [
    {
        "_id": "ORD-2026-0001",
        "product_id": "BATTERY-001",
        "supplier_id": "SUPPLIER-001",
        "destination_warehouse": "WAREHOUSE-001",
        "quantity_ordered": 10000,
        "unit_price": 500.0,
        "currency": "INR",
        "status": "CONFIRMED",
        "created_at": now
    }
]

# --------------------------------------------------
# 4. SHIPMENTS
# --------------------------------------------------
shipments = [
    {
        "_id": "SHIP-2026-0001",
        "order_id": "ORD-2026-0001",
        "product_id": "BATTERY-001",
        "quantity_claimed": 10000,
        "quantity_received": None,
        "origin": "SUPPLIER-001",
        "destination": "WAREHOUSE-001",
        "tracking_status": "AWAITING_VERIFICATION",
        "verification_status": "PENDING",
        "payment_status": "ON_HOLD",
        "created_at": now,
        "updated_at": now
    }
]

# --------------------------------------------------
# 5. PHYSICAL EVIDENCE
# Illustrative sample data for later verification tests
# --------------------------------------------------
physical_evidence = [
    {
        "_id": "EVD-0001",
        "shipment_id": "SHIP-2026-0001",
        "order_id": "ORD-2026-0001",
        "source_type": "SUPPLIER_REPORT",
        "reported_quantity": 10000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-SUP-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-0002",
        "shipment_id": "SHIP-2026-0001",
        "order_id": "ORD-2026-0001",
        "source_type": "INVENTORY_RECORD",
        "reported_quantity": 10000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-INV-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-0003",
        "shipment_id": "SHIP-2026-0001",
        "order_id": "ORD-2026-0001",
        "source_type": "RFID_SCAN",
        "reported_quantity": 9850,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-RFID-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-0004",
        "shipment_id": "SHIP-2026-0001",
        "order_id": "ORD-2026-0001",
        "source_type": "WEIGHT_ESTIMATE",
        "reported_quantity": 9850,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-WEIGHT-0001",
        "observed_at": now
    }
]

# --------------------------------------------------
# 6. PAYMENTS
# --------------------------------------------------
payments = [
    {
        "_id": "PAY-2026-0001",
        "order_id": "ORD-2026-0001",
        "shipment_id": "SHIP-2026-0001",
        "amount": 5000000.0,
        "currency": "INR",
        "status": "ON_HOLD",
        "hold_reason": "Shipment verification pending",
        "authorized": False,
        "created_at": now,
        "updated_at": now
    }
]
# 7. DISPLAY PRODUCT
display_product = {
    "_id": "DISPLAY-001",
    "product_name": "Display Unit",
    "category": "Display",
    "unit": "pieces",
    "unit_weight_kg": 0.5,
    "description": "Display units for electronic devices",
    "active": True,
    "created_at": now
}

# 8. DISPLAY INVENTORY
display_inventory = {
    "_id": "INV-DISPLAY-001",
    "product_id": "DISPLAY-001",
    "supplier_id": "SUPPLIER-001",
    "warehouse_id": "WAREHOUSE-001",
    "quantity_on_hand": 3000,
    "quantity_reserved": 0,
    "quantity_available": 3000,
    "updated_at": now
}

# 9. DISPLAY ORDER
display_order = {
    "_id": "ORD-2026-0002",
    "product_id": "DISPLAY-001",
    "supplier_id": "SUPPLIER-001",
    "destination_warehouse": "WAREHOUSE-001",
    "quantity_ordered": 3000,
    "unit_price": 1500.0,
    "currency": "INR",
    "status": "CONFIRMED",
    "created_at": now
}

# 10. DISPLAY SHIPMENT
display_shipment = {
    "_id": "SHIP-2026-0002",
    "order_id": "ORD-2026-0002",
    "product_id": "DISPLAY-001",
    "quantity_claimed": 3000,
    "quantity_received": 3000,
    "origin": "SUPPLIER-001",
    "destination": "WAREHOUSE-001",
    "tracking_status": "RECEIVED",
    "verification_status": "PENDING",
    "payment_status": "ON_HOLD",
    "created_at": now,
    "updated_at": now
}

# 11. DISPLAY PHYSICAL EVIDENCE
display_physical_evidence = [
    {
        "_id": "EVD-DIS-0001",
        "shipment_id": "SHIP-2026-0002",
        "order_id": "ORD-2026-0002",
        "source_type": "SUPPLIER_REPORT",
        "reported_quantity": 3000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-DIS-SUP-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-DIS-0002",
        "shipment_id": "SHIP-2026-0002",
        "order_id": "ORD-2026-0002",
        "source_type": "INVENTORY_RECORD",
        "reported_quantity": 3000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-DIS-INV-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-DIS-0003",
        "shipment_id": "SHIP-2026-0002",
        "order_id": "ORD-2026-0002",
        "source_type": "RFID_SCAN",
        "reported_quantity": 3000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-DIS-RFID-0001",
        "observed_at": now
    },
    {
        "_id": "EVD-DIS-0004",
        "shipment_id": "SHIP-2026-0002",
        "order_id": "ORD-2026-0002",
        "source_type": "WEIGHT_ESTIMATE",
        "reported_quantity": 3000,
        "evidence_status": "SIMULATED",
        "evidence_id": "SRC-DIS-WEIGHT-0001",
        "observed_at": now
    }
]

# 12. DISPLAY PAYMENT
display_payment = {
    "_id": "PAY-2026-0002",
    "order_id": "ORD-2026-0002",
    "shipment_id": "SHIP-2026-0002",
    "amount": 4500000.0,
    "currency": "INR",
    "status": "ON_HOLD",
    "hold_reason": "Awaiting shipment verification",
    "authorized": False,
    "created_at": now,
    "updated_at": now
}
# --------------------------------------------------
# Insert or update documents without duplicating IDs
# --------------------------------------------------
def upsert_documents(collection_name, documents):
    collection = db[collection_name]

    for document in documents:
        collection.replace_one(
            {"_id": document["_id"]},
            document,
            upsert=True
        )

    print(
        f"{collection_name}: "
        f"{collection.count_documents({})} total documents"
    )


def create_indexes():
    db.inventory.create_index(
        [("product_id", ASCENDING)]
    )
    db.orders.create_index(
        [("product_id", ASCENDING)]
    )
    db.shipments.create_index(
        [("order_id", ASCENDING)]
    )
    db.physical_evidence.create_index(
        [("shipment_id", ASCENDING)]
    )
    db.payments.create_index(
        [("shipment_id", ASCENDING)]
    )
    print("Indexes created successfully.")


def main():
    try:
        upsert_documents("products", products)
        upsert_documents("inventory", inventory)
        upsert_documents("orders", orders)
        upsert_documents("shipments", shipments)
        upsert_documents("physical_evidence", physical_evidence)
        upsert_documents("payments", payments)
        upsert_documents("products", [display_product])
        upsert_documents("inventory", [display_inventory])
        upsert_documents("orders", [display_order])
        upsert_documents("shipments", [display_shipment])
        upsert_documents("physical_evidence", display_physical_evidence)
        upsert_documents("payments", [display_payment])

        create_indexes()

        print("\nDatabase initialized successfully.")
        print(f"Database name: {DATABASE_NAME}")
        print("Sample order: ORD-2026-0001")
        print("Sample shipment: SHIP-2026-0001")
        print("Sample evidence is SIMULATED, not real sensor data.")

    except Exception as exc:
        print(f"Initialization failed: {exc}")
        raise

    finally:
        client.close()


if __name__ == "__main__":
    main()
