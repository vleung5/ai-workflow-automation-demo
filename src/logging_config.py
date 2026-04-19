"""Logging configuration - separated from general config"""

import logging
import logging.config
from typing import Optional

from src.config import config


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure application logging"""
    level = log_level or config.LOG_LEVEL

    formatter_class: str
    if config.DD_JSON_LOGGING:
        try:
            from pythonjsonlogger import jsonlogger  # noqa: F401

            formatter_class = "pythonjsonlogger.jsonlogger.JsonFormatter"
        except ImportError:
            formatter_class = "logging.Formatter"
    else:
        formatter_class = "logging.Formatter"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": formatter_class,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "json" if config.DD_JSON_LOGGING else "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)
    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"log_level": level, "json_logging": config.DD_JSON_LOGGING},
    )
