import asyncio
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


settings = get_settings()

async_database_url = str(settings.database_url).replace(
    "postgresql://",
    "postgresql+asyncpg://",
    1,
)
async_engine = create_async_engine(async_database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db


async def test_database_connection() -> bool:
    try:
        async with async_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.info("Conexão com o banco de dados realizada com sucesso.")
        return True
    except Exception:
        logger.exception("Erro ao conectar ao banco de dados.")
        return False


if __name__ == "__main__":
    is_connected = asyncio.run(test_database_connection())
    raise SystemExit(0 if is_connected else 1)
