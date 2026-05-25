import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.connection import Base, get_async_db
from app.main import app


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def mock_gemma_client(mocker):
    return mocker.patch(
        "app.llm.gemma_client.GemmaClient.generate",
        return_value="Resposta mockada da Gemma.",
    )


@pytest.fixture
def mock_task_repository(mocker):
    repository = mocker.Mock()
    repository.create_task = AsyncMock()
    repository.list_tasks = AsyncMock()
    repository.get_task = AsyncMock()
    repository.update_task = AsyncMock()
    repository.delete_task = AsyncMock()
    return repository


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    if not TEST_DATABASE_URL:
        pytest.skip("Defina TEST_DATABASE_URL para executar testes de integração.")

    database_name = make_url(TEST_DATABASE_URL).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL deve apontar para um banco de teste isolado.")

    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"timeout": 5},
    )
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    schema_created = False
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        schema_created = True

        async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
            async with TestingSessionLocal() as session:
                yield session

        app.dependency_overrides[get_async_db] = override_get_async_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        if schema_created:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
