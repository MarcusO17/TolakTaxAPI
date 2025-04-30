from fastapi import FastAPI, File, UploadFile, HTTPException
from groq import Groq
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/image/")
async def root():
    return {"message": "Hello World"}
