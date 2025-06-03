import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os

load_dotenv()


# Initialize Firebase Admin SDK
service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
if service_account_path:
    # Convert relative path to absolute path if needed
    if not os.path.isabs(service_account_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        service_account_path = os.path.join(base_dir, service_account_path.lstrip("./"))
    
    # Initialize Firebase with the service account key file
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)
else:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH not found in environment variables")


db = firestore.client()


def get_uid_from_id_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        return uid
    except auth.InvalidIdTokenError:
        print("Invalid ID token")
        return None
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

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


def add_receipt(receipt_data: dict, user_id: str):
    """
    Add a new receipt to the Firestore collection and associate it with a user.
    
    Args:
        receipt_data (dict): The receipt data to store
        user_id (str): The ID of the user who owns this receipt
    
    Returns:
        The document reference of the newly created receipt
    """
    # Add the user_id to the receipt data
    receipt_data["user_id"] = user_id
    
    # Add the receipt to Firestore
    doc_ref = db.collection("receipts").add(receipt_data)
    
    return doc_ref


def get_user_receipts(user_id: str):
    """
    Get all receipts belonging to a specific user.
    
    Args:
        user_id (str): The ID of the user whose receipts to retrieve
        
    Returns:
        List of receipt documents
    """
    receipts_ref = db.collection("receipts").where("user_id", "==", user_id).stream()
    return [receipt.to_dict() for receipt in receipts_ref]


def get_user(user_id: str):
    """
    Get user details from Firebase Authentication.
    
    Args:
        user_id (str): The ID of the user to retrieve
        
    Returns:
        User record or None if not found
    """
    try:
        return auth.get_user(user_id)
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


