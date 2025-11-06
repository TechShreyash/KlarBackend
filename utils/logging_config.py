# utils/logging_config.py

import logging
import sys


def setup_logging():
    """Configures the root logger."""

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a stream handler (console)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s (%(funcName)s): %(message)s"
    )
    handler.setFormatter(formatter)

    # Add the handler
    logger.addHandler(handler)
