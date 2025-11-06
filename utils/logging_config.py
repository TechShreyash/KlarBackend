import logging
import sys


def setup_logging():
    """Configures the root logger."""

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # This is your app's default level

    # Remove any existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a stream handler (console)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(
        logging.INFO
    )  # The handler processes all logs at INFO or higher

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s (%(funcName)s): %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the handler to the root logger
    root_logger.addHandler(console_handler)

    # Silence noisy third-party loggers by setting their level to WARNING

    logging.getLogger("google_genai").setLevel(logging.WARNING)
    logging.getLogger("google_genai.models").setLevel(logging.WARNING)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
