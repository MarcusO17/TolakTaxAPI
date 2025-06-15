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


# Load environment variables from .env file
load_dotenv()

# Load the receipt prompt from file
prompt_path = os.path.join(os.path.dirname(__file__), "receipt_prompt.txt")
with open(prompt_path, "r") as f:
    RECEIPT_PROMPT = f.read()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


app = FastAPI()





@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/upload-reciept-image/")
async def upload_reciept_image(file: Annotated[UploadFile, File()]):
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    with open(file.filename, "wb") as f:
        f.write(contents)

    return {"filename": file.filename}


@app.post("/read-reciept-image/")
async def read_reciept_image(file: Annotated[UploadFile, File()]):
    try:
        image = await file.read()
        base64_image = base64.b64encode(image).decode("utf-8")
        mime_type = file.content_type

        chat_completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            response_format={"type": "json_object"},
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

        return Receipt(**json.loads(chat_completion.choices[0].message.content))

    except Exception as e:
        return {"error": f"Could not read image: {str(e)}"}
    finally:
        await file.close()

@app.get("/user/get-username/")
async def get_username(id_token: str):
    user_id = db.get_uid_from_id_token(id_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    try:
        print(f"User ID: {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving username: {str(e)}")


@app.post("/add-receipt/")
async def add_receipt(receipt: Receipt, id_token: str):
    user_id = db.get_uid_from_id_token(id_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    receipt_data = Receipt.model_dump()
    receipt_data["user_id"] = user_id

    try:
        doc_ref = db.add_receipt(receipt_data, user_id,image_url)
        return {"message": "Receipt added successfully", "receipt_id": doc_ref.id}
    except Exception as e:
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
