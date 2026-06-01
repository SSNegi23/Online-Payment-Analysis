from pathlib import Path 
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from dotenv import load_dotenv

# Load the same .env file your ETL uses — no duplication of config
BASE_DIR = Path(__file__).resolve().parent.parent.parent 
load_dotenv(dotenv_path=BASE_DIR/"docker"/".env")

DB_USER     = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME     = os.getenv("POSTGRES_DB")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")

# asyncpg is the async PostgreSQL driver
# This is the connection string format SQLAlchemy expects for async postgres
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl=disable"

print(f"Connecting to: host={DB_HOST} port={DB_PORT} user={DB_USER} db={DB_NAME}")
# The engine manages the connection pool — one engine for the whole app
engine = create_async_engine(
    "postgresql+asyncpg://",   # empty URL — we pass everything via connect_args
    connect_args={
        "host":     DB_HOST,
        "port":     int(DB_PORT),
        "user":     DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "ssl":      False,
    },
    pool_pre_ping=True,
)

# SessionLocal is a factory — calling it creates a new DB session
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects usable after commit
)


class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this."""
    pass


async def get_db():
    """
    FastAPI dependency — yields a DB session to each request,
    then closes it automatically when the request is done.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
