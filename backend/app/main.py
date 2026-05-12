import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.mongo import connect_mongo, close_mongo
from app.redis_client import connect_redis, close_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
    logger.info("Starting AI Agent Orchestration Platform")

    await init_db()
    await connect_mongo()
    await connect_redis()

    from app.workers.pool import startup_pools, shutdown_pools
    startup_pools()

    if settings.OTLP_ENABLED:
        from app.observability.tracing import setup_tracing
        setup_tracing(app)

    yield

    shutdown_pools()
    await close_mongo()
    await close_redis()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Agent Orchestration Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

if settings.PROMETHEUS_ENABLED:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics")

from app.api.agents import router as agents_router
from app.api.workflows import router as workflows_router
from app.api.messages import router as messages_router
from app.api.monitoring import router as monitoring_router
from app.api.telegram import router as telegram_router
from app.api.websocket import router as ws_router

app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["Workflows"])
app.include_router(messages_router, prefix="/api/messages", tags=["Messages"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(ws_router, tags=["WebSocket"])


@app.get("/health")
async def health():
    return {"status": "ok"}
