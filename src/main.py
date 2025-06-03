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
import db_helper as db


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


@app.post("/upload-image/")
async def upload_image(file: Annotated[UploadFile, File()]):
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    with open(file.filename, "wb") as f:
        f.write(contents)

    return {"filename": file.filename}


@app.post("/read-uploaded-image/")
async def detect_image(file: Annotated[UploadFile, File()]):
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

        return {"message": chat_completion.choices[0].message.content, "receipt": json.loads(chat_completion.choices[0].message.content)}

    except Exception as e:
        return {"error": f"Could not read image: {str(e)}"}
    finally:
        await file.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
