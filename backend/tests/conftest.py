import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB_NAME"] = "test_agentplatform"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
os.environ["OTLP_ENABLED"] = "false"
os.environ["PROMETHEUS_ENABLED"] = "false"
os.environ["PROCESS_POOL_SIZE"] = "2"
os.environ["THREAD_POOL_SIZE"] = "2"

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
import app.models  # noqa: F401 — ensure all models are registered with Base.metadata

test_engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


mock_redis = MagicMock()
mock_redis.publish = AsyncMock()
mock_redis.set = AsyncMock(return_value=True)
mock_redis.xadd = AsyncMock()
mock_redis.xrevrange = AsyncMock(return_value=[])
mock_redis.pubsub = MagicMock(return_value=MagicMock(
    subscribe=AsyncMock(),
    unsubscribe=AsyncMock(),
    get_message=AsyncMock(return_value=None),
    aclose=AsyncMock(),
))


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    with (
        patch("app.mongo.connect_mongo", new_callable=AsyncMock),
        patch("app.mongo.close_mongo", new_callable=AsyncMock),
        patch("app.redis_client.connect_redis", new_callable=AsyncMock),
        patch("app.redis_client.close_redis", new_callable=AsyncMock),
        patch("app.redis_client.get_redis", return_value=mock_redis),
        patch("app.redis_client.publish", new_callable=AsyncMock),
        patch("app.redis_client.get_stream_history", new_callable=AsyncMock, return_value=[]),
        patch("app.workers.pool.startup_pools"),
        patch("app.workers.pool.shutdown_pools"),
        patch("app.database.init_db", new_callable=AsyncMock),
        patch(
            "app.services.telegram_service.invoke_agent_for_telegram",
            new_callable=AsyncMock,
            return_value="Test response from agent",
        ),
        patch(
            "app.services.telegram_service.send_message",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ),
    ):
        from app.main import app

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()


@pytest.fixture
def sample_agent_payload():
    return {
        "name": "Test Agent",
        "role": "tester",
        "system_prompt": "You are a test agent.",
        "model": "gpt-4o-mini",
        "tools": [],
        "channels": [],
        "memory_enabled": True,
        "memory_window": 10,
        "skills": ["testing"],
        "interaction_rules": {},
        "guardrails": {},
        "max_tokens": 1024,
        "temperature": 0.5,
    }
