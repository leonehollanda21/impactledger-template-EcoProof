from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


# ──────────────────────────────────────────────
# Base declarativa compartilhada por todos os models
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


import os

# ──────────────────────────────────────────────
# Engine assíncrono (asyncpg) — usado pela API
# ──────────────────────────────────────────────
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ──────────────────────────────────────────────
# Engine síncrono (psycopg2) — usado pelo Alembic
# ──────────────────────────────────────────────
db_url_sync = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or settings.DATABASE_URL_SYNC
if db_url_sync.startswith("postgres://"):
    db_url_sync = db_url_sync.replace("postgres://", "postgresql://", 1)
elif db_url_sync.startswith("postgresql+asyncpg://"):
    db_url_sync = db_url_sync.replace("postgresql+asyncpg://", "postgresql://", 1)

sync_engine = create_engine(
    db_url_sync,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
)


# ──────────────────────────────────────────────
# Dependency para injeção nas rotas FastAPI
# ──────────────────────────────────────────────
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
