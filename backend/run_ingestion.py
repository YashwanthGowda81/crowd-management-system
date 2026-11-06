"""
Dedicated Camera Ingestion Daemon Runner (Task 7.6.4).
Runs camera video decoding, YOLO inference, and live telemetry heartbeat updates.
Enforces single ownership via kernel lock; exits if another owner is already active.
"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion_daemon")

from app.ai.ingestion_manager import ingestion_coordinator
from app.routers.websocket import start_ai_processing_loop


async def main():
    if not ingestion_coordinator.acquire_ownership():
        owner_pid = ingestion_coordinator.get_owner_pid()
        pid_str = f"PID: {owner_pid}" if owner_pid is not None else "PID: unavailable (lock held by active owner)"
        logger.error(f"[INGESTION][FATAL] Another ingestion owner is already active ({pid_str}). Duplicate ingestion runner cannot start.")
        sys.exit(1)

    logger.info(f"[INGESTION][START] Dedicated camera ingestion daemon started successfully (PID: {os.getpid()}).")
    try:
        await start_ai_processing_loop()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("[INGESTION][STOP] Ingestion daemon stopping...")
    finally:
        ingestion_coordinator.release_ownership()


if __name__ == "__main__":
    asyncio.run(main())
