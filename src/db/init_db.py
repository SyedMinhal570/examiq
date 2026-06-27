"""
ExamIQ Database Initialization Script

Run:
    python -m src.db.init_db

This will:
  1. Create all tables defined in models.py
  2. Optionally seed initial admin user
"""

import asyncio
from src.db.models import Base, engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All database tables created successfully")


async def test_connection():
    """Verify DB connection is working."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except Exception as e:
        print("❌ Database connection failed:", e)
        raise


async def main():
    print("🚀 Initializing ExamIQ database...")

    await test_connection()
    await create_tables()

    print("🎉 Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())