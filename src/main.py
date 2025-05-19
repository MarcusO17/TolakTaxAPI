from fastapi import FastAPI, File, UploadFile, HTTPException
from groq import Groq
from dotenv import load_dotenv
import uuid
import os
import uvicorn 


load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    with open(file.filename, "wb") as f:
        f.write(contents)

    return {"filename": file.filename}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)