from fastapi import FastAPI, File, UploadFile, HTTPException
from groq import Groq
from dotenv import load_dotenv
import uuid
import os
import uvicorn
import base64
import json
import mimetypes
from typing import Annotated
from .classes.Reciept import Receipt 
from . import db_helper as db
import instructor


# Load environment variables from .env file
load_dotenv()

# Load the receipt prompt from file
prompt_path = os.path.join(os.path.dirname(__file__), "receipt_prompt.txt")
with open(prompt_path, "r") as f:
    RECEIPT_PROMPT = f.read()

# Load the tax prompt from file
prompt_path = os.path.join(os.path.dirname(__file__), "tax_prompt.txt")
with open(prompt_path, "r") as f:
    TAX_PROMPT = f.read()



client_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
client = instructor.from_groq(client_groq,mode=instructor.Mode.JSON)

app = FastAPI()





@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/upload-reciept-image/")
async def upload_reciept_image(file: Annotated[UploadFile, File()]):
    try:
        # Create a temporary file to save the uploaded content
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # Upload the temporary file to Minio
        image_url = db.upload_to_bucket(
            blob_name=f"receipts/{uuid.uuid4()}_{file.filename}",
            path_to_file=temp_file_path,
            bucket_name=os.environ.get("GOOGLE_BUCKET_NAME")
        )
        
        
        return {"image_url": image_url}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")
    finally:
        # Ensure the temporary file is removed
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/read-receipt-image/")
async def read_receipt_image(file: Annotated[UploadFile, File()]):
    try:
        image = await file.read()
        base64_image = base64.b64encode(image).decode("utf-8")
        mime_type = file.content_type

        receipt = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        response_model =Receipt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": RECEIPT_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        temperature=0.5,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )

        return receipt.model_dump()
    
    except Exception as e:
        return {"error": f"Could not read image: {str(e)}"}


@app.post("/add-receipt/")
async def add_receipt(id_token: str,file: Annotated[UploadFile, File()],receipt: str):
    print(receipt)
    await file.seek(0)  
    image_url = await upload_reciept_image(file)
    print(f"Image URL: {image_url['image_url']}")

    user_id = db.get_uid_from_id_token(id_token)
    print(f"User ID: {user_id}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    
    receipt_data = Receipt(**json.loads(receipt)).model_dump()
    print(f"Receipt Data: {receipt_data}")

    tax_info = await classify_tax(receipt_data)

    if "error" in receipt_data:
        raise HTTPException(status_code=400, detail=receipt_data["error"])
    
    try:
        doc_ref = db.add_receipt(receipt_data, user_id, image_url,tax_info)
        return {"message": "Receipt added successfully", "receipt_id": doc_ref[1].id}
    
    
    except Exception as e:
        print(f"Original error in add_receipt: {type(e).__name__} - {e}") # Print the original error
        raise HTTPException(status_code=500, detail=f"Error adding receipt: {str(e)}")

@app.get("/get-receipts-by-user/")
async def get_receipts_by_user(id_token: str):
    user_id = db.get_uid_from_id_token(id_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    try:
        print(f"User ID: {user_id}")
         # Retrieve receipts for the user
        receipts = db.get_user_receipts(user_id)
        return {"receipts": receipts}   
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving receipts: {str(e)}")

@app.get("/user/get-username/")
async def get_username(id_token: str):
    user_id = db.get_uid_from_id_token(id_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    try:
        print(f"User ID: {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving username: {str(e)}")
    
# Tax 

@app.get("/classify-tax/")
async def classify_tax(receipt_data:str):
    try:
        # Classify the tax
        tax_classification = client_groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": receipt+";"+TAX_PROMPT,
                    },
                ],
            }
        ],
        temperature=0.5,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
        )
        
        return {"tax_classification": json.loads(tax_classification.choices[0].message.content)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error classifying tax: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)