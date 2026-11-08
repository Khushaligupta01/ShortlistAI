from __future__ import annotations

import asyncio
import logging
import signal
import sys

from app.core.config import settings
from app.services.worker_service import worker_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shortlistai.worker.main")


async def main() -> None:
    logger.info("Initializing ShortlistAI Resume Processing Worker...")
    loop = asyncio.get_running_loop()

    def shutdown():
        logger.info("Shutdown signal received. Stopping worker...")
        worker_service.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop for add_signal_handler
            pass

    try:
        await worker_service.run_worker_loop(poll_interval=settings.WORKER_POLL_INTERVAL_SECONDS)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Worker interrupted.")
    finally:
        worker_service.stop()
        logger.info("Worker stopped successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
