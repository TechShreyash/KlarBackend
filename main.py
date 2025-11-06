# main.py
import asyncio
import logging

# Local imports
import config
from utils.logging_config import setup_logging
from utils.queueHandler import run_service

setup_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        asyncio.run(run_service())
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. Shutting down.")
    except Exception as e:
        logger.critical(f"A critical error occurred in main: {e}", exc_info=True)
