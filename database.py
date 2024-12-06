# database.py

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, String, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from models import Base  # Import Base from models.py

metadata = MetaData()
Base = declarative_base()

def get_db_url():
    load_dotenv()
    url = os.getenv("SUPABASE_DB")
    return url

# Create async engine
engine = create_async_engine(
    get_db_url(),
    echo=True,
    pool_size=5,
    max_overflow=10
)

# Create async session
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db(drop_existing=False):
    async with engine.begin() as conn:
        if drop_existing:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
