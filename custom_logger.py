"""
Logging configuration module for arXiv client.
Provides functions for setting up logging with different levels, formats and handlers.
"""

import sys
import logging
import coloredlogs
from utils import non_empty_check


def set_level(log_level: str):
    """
    Convert string log level to logging constant.

    :param log_level: String representation of log level (info, debug, warning, error, exception)
    :returns: Logging level constant
    :raises:
        TypeError: If log_level is not string
        ValueError: If log_level is empty
    """
    non_empty_check(variable=log_level, expected_type=str, variable_name="log level")
    log_level = log_level.lower()

    if "info" in log_level:
        return logging.INFO
    elif "deb" in log_level:
        return logging.DEBUG
    elif "warn" in log_level:
        return logging.WARNING
    elif "err" in log_level:
        return logging.ERROR
    elif "exc" in log_level:
        return logging.EXCEPTION
    else:
        return logging.INFO


def null_logger():
    """
    Create a logger that suppresses all output.

    :returns: Logger with NullHandler
    """
    null_logger = logging.getLogger("null_logger")
    null_logger.addHandler(logging.NullHandler())
    return null_logger


def setup_logger(name: str, log_level: str = "INFO"):
    """
    Configure and return a logger with console output and colored formatting.

    :param name: Name for the logger instance
    :param log_level: Logging level (info, debug, warning, error, exception)
    :returns: Configured logger instance
    :raises:
        TypeError: If name is not string
        ValueError: If name is empty

    Features:
        - Colored output using coloredlogs
        - Console handler writing to stdout
        - Formatted output with level, timestamp, file, line number
        - Prevents duplicate handlers
    """
    non_empty_check(variable=name, expected_type=str, variable_name="logger name")
    logger = logging.getLogger(name)
    logger.setLevel(set_level(log_level))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(set_level(log_level))
    formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s - %(filename)s: %(lineno)d - %(message)s"
    )
    console_handler.setFormatter(formatter)
    coloredlogs.install(level="DEBUG")
    coloredlogs.install(level="DEBUG", logger=logger)
    if not logger.hasHandlers():
        logger.addHandler(console_handler)
    return logger
