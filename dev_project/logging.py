"""Shared logging helpers for host-side and container-side odpm code."""

from __future__ import annotations

import logging
import os
import sys

ODPM_LOG_TAG = "[ODPM]"


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


class CustomFormatter(logging.Formatter):
    purple = "\x1b[1;35m"
    yellow = "\x1b[1;33m"
    red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[1;32m"

    def __init__(self, *, use_color: bool | None = None) -> None:
        super().__init__()
        self._use_color = _color_enabled() if use_color is None else use_color
        self._formats = self._build_formats(self._use_color)

    @classmethod
    def _build_formats(cls, use_color: bool) -> dict[int, str]:
        if use_color:
            format_info = (
                "%(asctime)s - {COLOR}" + ODPM_LOG_TAG + " %(levelname)s{RESET} - "
                "%(message)s"
            )
            format_other = (
                "%(asctime)s - {COLOR}" + ODPM_LOG_TAG + " %(levelname)s{RESET} - "
                "%(name)s - %(message)s (%(filename)s:%(lineno)d)"
            )
            return {
                logging.DEBUG: format_other.format(COLOR=cls.purple, RESET=cls.reset),
                logging.INFO: format_info.format(COLOR=cls.green, RESET=cls.reset),
                logging.WARNING: format_other.format(COLOR=cls.yellow, RESET=cls.reset),
                logging.ERROR: format_other.format(COLOR=cls.red, RESET=cls.reset),
                logging.CRITICAL: format_other.format(COLOR=cls.red, RESET=cls.reset),
            }
        format_info = "%(asctime)s - " + ODPM_LOG_TAG + " %(levelname)s - %(message)s"
        format_other = (
            "%(asctime)s - "
            + ODPM_LOG_TAG
            + " %(levelname)s - %(name)s - %(message)s (%(filename)s:%(lineno)d)"
        )
        return {
            logging.DEBUG: format_other,
            logging.INFO: format_info,
            logging.WARNING: format_other,
            logging.ERROR: format_other,
            logging.CRITICAL: format_other,
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self._formats.get(record.levelno, self._formats[logging.INFO])
        return logging.Formatter(log_fmt).format(record)


def get_module_logger(mod_name: str = "") -> logging.Logger:
    """
    To use this, do logger = get_module_logger(__name__)
    """
    logger = logging.getLogger(mod_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(CustomFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
