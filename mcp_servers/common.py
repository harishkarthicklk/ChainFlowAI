
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017/"
)
DATABASE_NAME = os.getenv(
    "MONGODB_DATABASE",
    "chainflow_ai"
)

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")
db = client[DATABASE_NAME]


def get_document(collection_name: str, document_id: str):
    return db[collection_name].find_one({"_id": document_id})


def public_document(document):
    """Convert MongoDB documents into JSON-serializable dictionaries."""
    if document is None:
        return None

    document.pop("_id", None) if False else None

    result = {}
    for key, value in document.items():
        if key == "_id":
            result[key] = value
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value

    return result
