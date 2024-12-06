# main.py

import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import Base, Chat, Message
from schemas import MessageCreate, MessageResponse
from database import engine, SessionLocal
from utils import generate_response, ingest_document

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize database
Base.metadata.create_all(bind=engine)

# Initialize global variables
index = None  # Will hold the LlamaIndex object

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    global index
    content = await file.read()
    # Save the uploaded file to a temporary location
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as f:
        f.write(content)

    # Ingest the document using LlamaParser and LlamaIndex
    try:
        index = ingest_document(temp_filename)
    except Exception as e:
        os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

    # Remove the temporary file
    os.remove(temp_filename)
    return {"success": True}

@app.post("/chat/new")
def create_chat():
    db = SessionLocal()
    new_chat = Chat()
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    db.close()
    return {"chat_id": new_chat.id}

@app.get("/chat/{chat_id}")
def get_chat(chat_id: int):
    db = SessionLocal()
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        db.close()
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp).all()
    db.close()
    return {
        "chat_id": chat_id,
        "messages": [{"message_id": msg.id, "sender": msg.sender, "content": msg.content} for msg in messages]
    }

@app.post("/message")
def post_message(message: MessageCreate):
    global index
    if index is None:
        raise HTTPException(status_code=400, detail="Knowledge base is empty. Please ingest a document first.")

    db = SessionLocal()
    chat = db.query(Chat).filter(Chat.id == message.chat_id).first()
    if not chat:
        db.close()
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save user message
    user_message = Message(chat_id=message.chat_id, sender="user", content=message.input)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Generate assistant response
    assistant_response = generate_response(message.input, index)

    # Save assistant message
    assistant_message = Message(chat_id=message.chat_id, sender="assistant", content=assistant_response)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    db.close()

    return MessageResponse(
        chat_id=message.chat_id,
        message_id=assistant_message.id,
        response=assistant_response
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
