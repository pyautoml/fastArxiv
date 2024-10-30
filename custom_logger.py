import sys
import logging
from utils import non_empty_check


def set_level(log_level: str):
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
    null_logger = logging.getLogger("null_logger")
    null_logger.addHandler(logging.NullHandler())
    return null_logger


def setup_logger(name: str, log_level: str = "INFO"):
    non_empty_check(variable=name, expected_type=str, variable_name="logger name")
    logger = logging.getLogger(name)
    logger.setLevel(set_level(log_level))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(set_level(log_level))
    formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s - %(filename)s: %(lineno)d - %(message)s"
    )
    console_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(console_handler)
    return logger
