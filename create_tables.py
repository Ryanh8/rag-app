import asyncio
from database import engine
from models import Base

async def create_tables():
    async with engine.begin() as conn:
        # Drop existing tables if they exist
        await conn.run_sync(Base.metadata.drop_all)
        # Create tables from SQLAlchemy models
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully")

if __name__ == "__main__":
    asyncio.run(create_tables()) 