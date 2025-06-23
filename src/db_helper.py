import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
from .classes.Reciept import LineTax
import json
import base64
import re
import os
from google.cloud import storage



load_dotenv()
def get_firebase_credentials():
    firebase_encoded_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    firebase_encoded_key = str(firebase_encoded_key)[2:-1]
    return json.loads(base64.b64decode(firebase_encoded_key).decode('utf-8'))

def get_google_credentials():
    google_encoded_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    google_encoded_key = str(google_encoded_key)[2:-1]
    return json.loads(base64.b64decode(google_encoded_key).decode('utf-8'))


firebase_sak = get_firebase_credentials()
google_sak = get_google_credentials()


# Initialize Firebase with the service account key file
cred = credentials.Certificate(firebase_sak)
firebase_admin.initialize_app(cred)

#Google Cloud Storage client
google_bucket = storage.Client.from_service_account_info(google_sak)

db = firestore.client()

def upload_to_bucket(blob_name, path_to_file, bucket_name):
    """ Upload data to a bucket"""
     
    bucket = google_bucket.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    
    #returns a public url
    return blob.public_url


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


def add_receipt(receipt_data: dict, user_id: str,image_url: str):
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
    receipt_data["image_url"] = image_url
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

def enrich_receipt_tax_info(receipt_data: dict,tax_classification: dict = None):
    """
    Parse tax information into line items.
    
    Args:
        receipt_data (dict): The receipt data containing tax information
        
    Returns:
        List of line items with tax information
    """

    try:
        for i, item in enumerate(receipt_data["line_items"]):
            if tax_classification and 'items' in tax_classification and i < len(tax_classification['items']):
                item["line_tax"] = LineTax(**tax_classification['items'][i]).model_dump()
            else:
                item["line_tax"] = None 
            
        
    
        tax_summary = {
            "total_tax_saved": 0.0,
            "exempt_items_count": 0,
            "taxable_items_count": 0,
            "taxable_items": [],
        }
        

        for item in receipt_data["line_items"]:
            if item["line_tax"] is not None and item["line_tax"].get('tax_eligible') == True:
                tax_summary["taxable_items_count"] += 1
                tax_summary["total_tax_saved"] += item["line_tax"].get('tax_amount', 0)
                tax_summary["taxable_items"].append(item["line_tax"])
            else:
                tax_summary["exempt_items_count"] += 1
               
        # Add tax summary to receipt data
        receipt_data["tax_info"] = tax_summary

        return receipt_data

    except Exception as e:
        print(f"Error parsing tax into line items: {e}")
        receipt_data["error"] = "Failed to parse tax information"
        return receipt_data
            
        
def clean_bad_json_response(response_content):
    """
    Extract and clean JSON from LLM response that might include markdown formatting
    or incomplete JSON.
    """
    cleaned_content = response_content.strip()
    if cleaned_content.startswith("```json"):
        match = re.search(r"```json\s*([\s\S]*?)\s*```", cleaned_content)
        if match:
            cleaned_content = match.group(1)

    if not cleaned_content.startswith("{"):
        cleaned_content = "{" + cleaned_content
    if not cleaned_content.endswith("}"):
        cleaned_content = cleaned_content + "}"

    return json.loads(cleaned_content)

