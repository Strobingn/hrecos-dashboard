import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/hrecos"
)

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    poolclass=NullPool,  # Use NullPool for serverless/async environments
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """Dependency for FastAPI to get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
