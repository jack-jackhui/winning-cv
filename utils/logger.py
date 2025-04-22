import logging
import sys
from pathlib import Path


def setup_logger(log_file=None, level=logging.DEBUG):
    """Configure root logger with handlers and third-party log levels"""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler (all levels)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # Console handler (info+ only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Configure third-party loggers centrally here
    third_party_loggers = {
        'azure': logging.WARNING,
        'fontTools.subset': logging.WARNING,
        'fontTools.ttLib': logging.WARNING
    }

    for logger_name, log_level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(log_level)

    return root_logger
