"""Shared logging helpers for host-side and container-side odpm code."""

import logging


class CustomFormatter(logging.Formatter):

    purple = "\x1b[1;35m"
    yellow = "\x1b[1;33m"
    red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[1;32m"

    format_info = "%(asctime)s - {COLOR}%(levelname)s{RESET} - %(message)s"
    format_other = (
        "%(asctime)s - %(name)s - {COLOR}%(levelname)s{RESET} - "
        "%(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: format_other.format(
            COLOR=purple,
            RESET=reset,
        ),
        logging.INFO: format_info.format(
            COLOR=green,
            RESET=reset,
        ),
        logging.WARNING: format_other.format(
            COLOR=yellow,
            RESET=reset,
        ),
        logging.ERROR: format_other.format(
            COLOR=red,
            RESET=reset,
        ),
        logging.CRITICAL: format_other.format(
            COLOR=red,
            RESET=reset,
        ),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_module_logger(mod_name=""):
    """
    To use this, do logger = get_module_logger(__name__)
    """
    logger = logging.getLogger(mod_name)
    handler = logging.StreamHandler()
    formatter = CustomFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
