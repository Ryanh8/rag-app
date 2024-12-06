# main.py

import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import Base, Chat, Message
from schemas import MessageCreate, MessageResponse
from database import engine, SessionLocal
from utils import PineconeRAGManager

# Load environment variables
load_dotenv()

app = FastAPI()
rag_manager = PineconeRAGManager()

# Initialize database
Base.metadata.create_all(bind=engine)

# Initialize global variables
index = None  # Will hold the LlamaIndex object

@app.post("/ingest")
async def ingest(chat_id: int, file: UploadFile = File(...)):
    content = await file.read()
    temp_filename = f"temp_{file.filename}"
    
    try:
        with open(temp_filename, "wb") as f:
            f.write(content)
        
        await rag_manager.ingest_document(temp_filename, chat_id)
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

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
async def post_message(message: MessageCreate):
    db = SessionLocal()
    try:
        # Verify chat exists
        chat = db.query(Chat).filter(Chat.id == message.chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Save user message
        user_message = Message(
            chat_id=message.chat_id,
            sender="user",
            content=message.input
        )
        db.add(user_message)
        db.commit()

        # Generate response
        response = await rag_manager.generate_response(
            message.input,
            message.chat_id
        )

        # Save assistant message
        assistant_message = Message(
            chat_id=message.chat_id,
            sender="assistant",
            content=response
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        return MessageResponse(
            chat_id=message.chat_id,
            message_id=assistant_message.id,
            response=response
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
