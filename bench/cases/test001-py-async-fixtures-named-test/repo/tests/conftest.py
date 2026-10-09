from collections.abc import AsyncGenerator

import pytest_asyncio
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db import create_test_engine


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Return the test database engine."""
    engine = create_test_engine()
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture()
async def test_sessionmaker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=test_engine, expire_on_commit=False)


@async_fixture
async def test_db(test_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    async with test_sessionmaker() as session:
        yield session
