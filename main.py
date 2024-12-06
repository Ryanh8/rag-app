# main.py

import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, init_db
from models import Chat, Message
from schemas import MessageCreate, MessageResponse
from utils import PineconeRAGManager

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_manager = PineconeRAGManager()
logging.basicConfig(level=logging.INFO)

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        logging.info("✅ Database initialized successfully")
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {str(e)}")
        raise

@app.post("/chat/new")
async def create_chat(db: AsyncSession = Depends(get_db)):
    new_chat = Chat()
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return {"chat_id": new_chat.id}

@app.get("/chat/{chat_id}")
async def get_chat(chat_id: int, db: AsyncSession = Depends(get_db)):
    # Get chat with messages
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get messages for chat
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return {
        "chat_id": chat_id,
        "messages": [
            {
                "message_id": msg.id,
                "sender": msg.sender,
                "content": msg.content
            } for msg in messages
        ]
    }

@app.get("/chats")
async def get_all_chats(db: AsyncSession = Depends(get_db)):
    # Get all chats with their messages
    result = await db.execute(
        select(Chat).order_by(Chat.created_at.desc())
    )
    chats = result.scalars().all()
    
    chat_list = []
    for chat in chats:
        # Get messages for each chat
        messages_result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat.id)
            .order_by(Message.created_at)
        )
        messages = messages_result.scalars().all()
        
        chat_list.append({
            "id": chat.id,
            "messages": [
                {
                    "content": msg.content,
                    "sender": msg.sender
                } for msg in messages
            ]
        })
    
    return chat_list

@app.post("/message")
async def post_message(message: MessageCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Verify chat exists
        result = await db.execute(
            select(Chat).where(Chat.id == message.chat_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Save user message
        user_message = Message(
            chat_id=message.chat_id,
            sender="user",
            content=message.input
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)

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
        await db.commit()
        await db.refresh(assistant_message)

        return MessageResponse(
            chat_id=message.chat_id,
            message_id=assistant_message.id,
            response=response
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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

