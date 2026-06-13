"""Localized host-side human summaries (A1b). Container raw logs stay English."""

from __future__ import annotations

from .logging import get_module_logger
from .translations import _

_logger = get_module_logger(__name__)

MSG_PREPARE_STARTED = (
    "Preparing your Odoo environment (dependencies, templates, compose files)..."
)
MSG_PREPARE_COMPLETED = "Project files are ready."
MSG_STARTING_CONTAINERS = "Starting containers with Docker Compose..."
MSG_COMPOSE_STACK_HEALTHY = (
    "Compose stack is healthy; reusing existing containers without --force-recreate"
)
MSG_CONTAINER_LOGS_ENGLISH = (
    "Attached to container output. Detailed technical logs below are in English."
)
MSG_ODOO_URL_HINT = "When Odoo is ready, open http://localhost:{ODOO_PORT}"
MSG_UPDATE_LOCK_SKIP = "Git dependency lock updated; container start skipped."
MSG_SKIP_START = "Container start skipped (--skip-start)."
MSG_COMPOSE_FAILED = "docker compose up failed with exit code {EXIT_CODE}"
MSG_COMPOSE_FAILED_HINT = (
    "Check `docker compose ps` and the English log output above for details."
)
MSG_CONTROL_C = "Control+C pressed; stopping."

SUMMARY_MSGIDS = (
    MSG_PREPARE_STARTED,
    MSG_PREPARE_COMPLETED,
    MSG_STARTING_CONTAINERS,
    MSG_COMPOSE_STACK_HEALTHY,
    MSG_CONTAINER_LOGS_ENGLISH,
    MSG_ODOO_URL_HINT,
    MSG_UPDATE_LOCK_SKIP,
    MSG_SKIP_START,
    MSG_COMPOSE_FAILED,
    MSG_COMPOSE_FAILED_HINT,
    MSG_CONTROL_C,
)


def log_prepare_started() -> None:
    _logger.info(_(MSG_PREPARE_STARTED))


def log_prepare_completed() -> None:
    _logger.info(_(MSG_PREPARE_COMPLETED))


def log_compose_stack_healthy() -> None:
    _logger.info(_(MSG_COMPOSE_STACK_HEALTHY))


def log_starting_containers(*, odoo_port: int) -> None:
    _logger.info(_(MSG_STARTING_CONTAINERS))
    _logger.info(_(MSG_CONTAINER_LOGS_ENGLISH))
    _logger.info(_(MSG_ODOO_URL_HINT).format(ODOO_PORT=odoo_port))


def log_update_lock_skip() -> None:
    _logger.info(_(MSG_UPDATE_LOCK_SKIP))


def log_skip_start() -> None:
    _logger.info(_(MSG_SKIP_START))


def log_compose_failed(exit_code: int) -> None:
    _logger.error(_(MSG_COMPOSE_FAILED).format(EXIT_CODE=exit_code))
    _logger.error(_(MSG_COMPOSE_FAILED_HINT))


def log_control_c() -> None:
    _logger.info(_(MSG_CONTROL_C))
