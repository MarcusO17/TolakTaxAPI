import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

load_dotenv()


# Initialize Firebase Admin SDK
cred = credentials.Certificate(os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"))
firebase_admin.initialize_app(cred)


db = firestore.client()

def get_receipt_by_id(receipt_id: str):
    """
    Get a receipt by its ID.
    """
    return db.collection("receipts").document(receipt_id).get()

def get_receipt_collection():
    """
    Get the Firestore collection for receipts.
    """
    return db.collection("receipts")


def add_receipt(receipt_data: dict):
    """
    Add a new receipt to the Firestore collection.
    """
    return db.collection("receipts").add(receipt_data)


