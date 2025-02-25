"""
This module provides logging config for reuse in other modules
"""

import logging
from logging.handlers import RotatingFileHandler
import os

# Dynamically determine the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # Get the directory of logging_config.py
PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)  # Move up to the project root

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure logs directory exists

LOG_FILENAME = os.path.join(LOG_DIR, "rankings.log")
LOGGING_LEVEL = logging.INFO

file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

logging.basicConfig(
    encoding="utf-8",
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler],
)

logger = logging.getLogger("rankings_logger")
