"""Logging configuration setup."""

import logging
from datetime import datetime
from os import mkdir

from .settings import settings

settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging() -> logging.Logger:
    """Configure logging with file and console handlers."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                settings.LOGS_DIR / f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
            ),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger()
    # Set console handler to INFO level (file handler stays DEBUG)
    logger.handlers[1].setLevel(logging.INFO)
    
    return logger