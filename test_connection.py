import asyncio
from database import engine, init_db
import logging

logging.basicConfig(level=logging.INFO)

async def test_connection():
    try:
        await init_db()
        print("✅ Database connection test passed")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())