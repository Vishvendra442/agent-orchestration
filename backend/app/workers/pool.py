import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from app.config import settings

logger = logging.getLogger(__name__)

SHUTDOWN_TIMEOUT_S = 30

process_pool: ProcessPoolExecutor | None = None
thread_pool: ThreadPoolExecutor | None = None


def startup_pools():
    global process_pool, thread_pool
    process_pool = ProcessPoolExecutor(max_workers=settings.PROCESS_POOL_SIZE)
    thread_pool = ThreadPoolExecutor(
        max_workers=settings.THREAD_POOL_SIZE,
        thread_name_prefix="agent-io",
    )
    logger.info(
        "Pools started: process=%d, thread=%d",
        settings.PROCESS_POOL_SIZE,
        settings.THREAD_POOL_SIZE,
    )


def shutdown_pools():
    global process_pool, thread_pool
    if thread_pool:
        logger.info("Shutting down thread pool (timeout=%ds)...", SHUTDOWN_TIMEOUT_S)
        thread_pool.shutdown(wait=True, cancel_futures=True)
    if process_pool:
        logger.info("Shutting down process pool (timeout=%ds)...", SHUTDOWN_TIMEOUT_S)
        process_pool.shutdown(wait=True, cancel_futures=True)
    logger.info("All pools shut down")


def get_process_pool() -> ProcessPoolExecutor:
    if process_pool is None:
        raise RuntimeError("Process pool not initialized")
    return process_pool


def get_thread_pool() -> ThreadPoolExecutor:
    if thread_pool is None:
        raise RuntimeError("Thread pool not initialized")
    return thread_pool
