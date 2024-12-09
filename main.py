# main.py

import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, init_db
from models import Chat, Message
from schemas import MessageCreate, MessageResponse
from utils import PineconeRAGManager
import datetime
import aiofiles

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://81f8-2601-647-6900-e88-50fb-b9d9-a560-17a8.ngrok-free.app"],  # Your frontend URL
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

@app.on_event("startup")
async def print_routes():
    logging.info("🛣️ Registered routes:")
    for route in app.routes:
        logging.info(f"{route.methods} {route.path}")

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

    logging.info(f"🚀 Ingesting file: {file.filename}")
    
    try:
        # Use async file operations
        async with aiofiles.open(temp_filename, "wb") as f:
            await f.write(content)
        
        await rag_manager.ingest_document(temp_filename, chat_id)
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/webhook/notion")
async def notion_webhook(request: Request):
    logging.info("⭐ Entering webhook endpoint")
    try:
        body = await request.body()
        logging.info(f"Raw request body: {body}")
        
        headers = dict(request.headers)
        logging.info(f"Request headers: {headers}")
        
        payload = await request.json()
        logging.info(f"Parsed payload: {payload}")
        
        # Handle automation events
        if payload.get("source", {}).get("type") == "automation":
            page_id = payload.get("data", {}).get("id")
            if page_id:
                logging.info(f"🔄 Processing page update for ID: {page_id}")
                index = await rag_manager.update_notion_page(page_id)
                return {"success": True, "index_id": str(index.index_id)}
        
        # Handle direct page updates
        if payload.get("type") == "page_updated":
            page_id = payload.get("page", {}).get("id")
            if page_id:
                logging.info(f"🔄 Processing direct page update for ID: {page_id}")
                await rag_manager.update_notion_page(page_id)
                return {"success": True}
        
        logging.info("⏭️ Skipping non-page event")
        return {"success": True, "message": "Event type not handled"}
        
    except Exception as e:
        logging.error(f"❌ Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"🚀 Request received: {request.method} {request.url}")
    logging.info(f"🔑 Headers: {dict(request.headers)}")
    try:
        response = await call_next(request)
        logging.info(f"✅ Response status: {response.status_code}")
        return response
    except Exception as e:
        logging.error(f"❌ Middleware error: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    logging.info("🏥 Health check endpoint hit")
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/webhook/notion/health")
async def webhook_health():
    logging.info("🏥 Webhook health check endpoint hit")
    return {
        "status": "webhook endpoint healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }

