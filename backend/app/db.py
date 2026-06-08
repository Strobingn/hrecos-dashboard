import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for local dev when no PostgreSQL available
# Store in project directory for persistence across reboots
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SQLITE_PATH = os.path.join(PROJECT_DIR, "hrecos.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"
)

# SQLite needs StaticPool + connect_args for async use
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
