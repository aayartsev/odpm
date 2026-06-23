"""Interactive wizard for first-time host ``.env`` creation."""

from __future__ import annotations

import os
from pathlib import Path

from .. import constants
from ..debugger.backends import DEBUGGER_BACKENDS
from ..debugger.constants import (
    DEBUGGER_BACKEND_LABELS,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_DEBUGGER_CONNECT_HOST,
    DEFAULT_ODPM_IDE,
    ODPM_IDE_LABELS,
    ODPM_IDE_VALUES,
)
from ..logging import get_module_logger
from ..translations import _, parse_odpm_locale_setting

_logger = get_module_logger(__name__)


def _prompt_input(prompt: str) -> str:
    from ..interactive import prompt_input

    return prompt_input(prompt)


def get_from_user_odoo_projects_src_dir() -> str:
    default_odoo_projects_src_dir = os.path.join(Path.home(), "odoo_projects")
    user_dir = _prompt_input(
        _(
            "Set other odoo projects sources directory, You can leave default "
            "{DEFAULT_ODOO_PROJECTS_SRC_DIR} or write your own. Press 'Enter' "
            "to leave default value:"
        ).format(
            DEFAULT_ODOO_PROJECTS_SRC_DIR=default_odoo_projects_src_dir,
        )
    )
    if not user_dir:
        user_dir = default_odoo_projects_src_dir
    _logger.info(
        _(
            "You select this other odoo projects sources dir: "
            "{SELECTED_ODOO_PROJECTS_DIR}\n"
        ).format(
            SELECTED_ODOO_PROJECTS_DIR=user_dir,
        )
    )
    return user_dir


def get_from_user_backup_dir() -> str:
    default_backup_dir = os.path.join(Path.home(), "odoo_backups")
    user_dir = _prompt_input(
        _(
            "Set directory for odoo creating/restoring backups, You can leave "
            "default {DEFAULT_ODOO_BACKUP_DIR} or write your own. Press "
            "'Enter' to leave default value:"
        ).format(
            DEFAULT_ODOO_BACKUP_DIR=default_backup_dir,
        )
    )
    if not user_dir:
        user_dir = default_backup_dir
    _logger.info(
        _(
            "You select this odoo backups dir: {SELECTED_ODOO_BACKUPS_DIR}\n"
        ).format(
            SELECTED_ODOO_BACKUPS_DIR=user_dir,
        )
    )
    return user_dir


def get_from_user_odoo_port() -> int:
    default_port = constants.ODOO_DEFAULT_PORT
    port = _prompt_input(
        _(
            "Set odoo port which it will listen. You can leave default "
            "{DEFAULT_ODOO_PORT} or write your own. Press 'Enter' to leave "
            "default value:\n"
        ).format(
            DEFAULT_ODOO_PORT=default_port,
        )
    )
    if not port:
        port = default_port
    _logger.info(
        _(
            "You select this port for which odoo will listen: "
            "{SELECTED_ODOO_PORT}\n"
        ).format(
            SELECTED_ODOO_PORT=default_port,
        )
    )
    return int(port)


def get_from_user_postgres_port() -> int:
    default_port = constants.POSTGRES_DEFAULT_PORT
    port = _prompt_input(
        _(
            "Set PostgreSQL database server port which it will listen. You can "
            "leave default {DEFAULT_POSTGRES_PORT} or write your own. Press "
            "'Enter' to leave default value:\n"
        ).format(
            DEFAULT_POSTGRES_PORT=default_port,
        )
    )
    if not port:
        port = default_port
    _logger.info(
        _(
            "You select this port for which PostgreSQL database server will "
            "listen: {SELECTED_POSTGRES_PORT}\n"
        ).format(
            SELECTED_POSTGRES_PORT=default_port,
        )
    )
    return int(port)


def get_from_user_debugger_port() -> int:
    default_port = constants.DEBUGGER_DEFAULT_PORT
    port = _prompt_input(
        _(
            "Set debugger port which it will listen. You can leave default "
            "{DEFAULT_DEBUGGER_PORT} or write your own. Press 'Enter' to leave "
            "default value:\n"
        ).format(
            DEFAULT_DEBUGGER_PORT=default_port,
        )
    )
    if not port:
        port = default_port
    _logger.info(
        _(
            "You select this port for which Python Debugger will listen: "
            "{SELECTED_DEBUGGER_PORT}\n"
        ).format(
            SELECTED_DEBUGGER_PORT=default_port,
        )
    )
    return int(port)


def get_from_user_gevent_port() -> int:
    default_port = constants.GEVENT_DEFAULT_PORT
    port = _prompt_input(
        _(
            "Set gevent port which it will listen. You can leave default "
            "{DEFAULT_GEVENT_PORT} or write your own. Press 'Enter' to leave "
            "default value:\n"
        ).format(
            DEFAULT_GEVENT_PORT=default_port,
        )
    )
    if not port:
        port = default_port
    _logger.info(
        _(
            "You select this port for which Odoo Gevent Websocket System will "
            "listen: {SELECTED_GEVENT_PORT}\n"
        ).format(
            SELECTED_GEVENT_PORT=default_port,
        )
    )
    return int(port)


def get_from_user_odpm_scenario() -> str:
    default_odpm_scenario = constants.DEFAULT_ODPM_SCENARIO
    list_of_scenarios = "\n"
    for scenario in constants.ODPM_SCENARIOS.items():
        list_of_scenarios += f"{scenario[0]} - {scenario[1]}\n"
    odpm_scenario_key = _prompt_input(
        _(
            "Please select scenario by number of odpm usage from this list "
            "{LIST_OF_SCENARIOS}\n Press 'Enter' to leave default value:\n"
        ).format(
            LIST_OF_SCENARIOS=list_of_scenarios,
        )
    )

    if not odpm_scenario_key:
        selected_scenario = default_odpm_scenario
    else:
        odpm_scenario_key = int(odpm_scenario_key)
        selected_scenario = constants.ODPM_SCENARIOS.get(
            odpm_scenario_key, default_odpm_scenario
        )
    _logger.info(
        _("You select {SELECTED_ODPM_SCENARIO} scenario  for odpm usage\n").format(
            SELECTED_ODPM_SCENARIO=selected_scenario,
        )
    )
    return str(selected_scenario)


def get_from_user_odpm_locale() -> str:
    from ..translations import _locale_from_environment

    system_locale = _locale_from_environment()
    user_locale = _prompt_input(
        _(
            "Set odpm host message language. System locale is {SYSTEM_LOCALE}. "
            "Press 'Enter' to keep the system default or type a locale "
            "(for example ru_RU):"
        ).format(SYSTEM_LOCALE=system_locale)
    )
    if not user_locale:
        _logger.info(
            _(
                "You selected the system default locale for odpm messages: "
                "{SELECTED_LOCALE}\n"
            ).format(SELECTED_LOCALE=system_locale)
        )
        return ""
    parsed_locale = parse_odpm_locale_setting(user_locale)
    if parsed_locale is None:
        _logger.warning(
            _("Invalid %s=%r, using system locale %s"),
            constants.ODPM_LOCALE_ENV_KEY,
            user_locale,
            system_locale,
        )
        return ""
    _logger.info(
        _(
            "You selected this locale for odpm messages: {SELECTED_LOCALE}\n"
        ).format(SELECTED_LOCALE=parsed_locale)
    )
    return parsed_locale


def get_from_user_debugger_connect_host() -> str:
    default_host = DEFAULT_DEBUGGER_CONNECT_HOST
    user_host = _prompt_input(
        _(
            "Set IDE host name for pydevd_connect (container connects to Debug "
            "Server). Press 'Enter' for default {DEFAULT_HOST}:\n"
        ).format(DEFAULT_HOST=default_host)
    )
    if not user_host:
        selected = default_host
    else:
        from ..debugger.env_parsing import parse_debugger_connect_host

        selected = parse_debugger_connect_host(user_host)
    _logger.info(
        _("You selected debugger connect host: {SELECTED_HOST}\n").format(
            SELECTED_HOST=selected,
        )
    )
    return selected


def get_from_user_debugger_suspend() -> bool:
    from ..debugger.env_parsing import parse_debugger_suspend

    choice = _prompt_input(
        _(
            "Suspend Odoo until PyCharm Debug Server connects? "
            "Answer y/yes or n/no (Enter for no):\n"
        )
    )
    selected = parse_debugger_suspend(choice)
    _logger.info(
        _("You selected debugger suspend on connect: {SELECTED_SUSPEND}\n").format(
            SELECTED_SUSPEND="yes" if selected else "no"
        )
    )
    return selected


def get_from_user_debugger_backend() -> str:
    default_backend = DEFAULT_DEBUGGER_BACKEND
    available_backends = sorted(DEBUGGER_BACKENDS)
    options = "\n".join(
        f"{index} - {DEBUGGER_BACKEND_LABELS.get(backend_id, backend_id)}"
        for index, backend_id in enumerate(available_backends, start=1)
    )
    choice = _prompt_input(
        _(
            "Select debugger backend for developer scenario "
            "(Enter for default {DEFAULT_BACKEND}):\n{OPTIONS}\n"
        ).format(DEFAULT_BACKEND=default_backend, OPTIONS=options)
    )
    if not choice:
        selected = default_backend
    else:
        try:
            selected = available_backends[int(choice) - 1]
        except (ValueError, IndexError):
            _logger.warning(
                _("Invalid debugger backend choice %r, using %s"),
                choice,
                default_backend,
            )
            selected = default_backend
    _logger.info(
        _("You selected debugger backend: {SELECTED_BACKEND}\n").format(
            SELECTED_BACKEND=selected,
        )
    )
    return selected


def get_from_user_odpm_ide() -> str:
    default_ide = DEFAULT_ODPM_IDE
    options = "\n".join(
        f"{index} - {ODPM_IDE_LABELS[ide_id]}"
        for index, ide_id in enumerate(sorted(ODPM_IDE_VALUES), start=1)
    )
    choice = _prompt_input(
        _(
            "Select IDE configuration to generate "
            "(Enter for default {DEFAULT_IDE}):\n{OPTIONS}\n"
        ).format(DEFAULT_IDE=default_ide, OPTIONS=options)
    )
    if not choice:
        selected = default_ide
    else:
        ordered = sorted(ODPM_IDE_VALUES)
        try:
            selected = ordered[int(choice) - 1]
        except (ValueError, IndexError):
            _logger.warning(
                _("Invalid ODPM_IDE choice %r, using %s"),
                choice,
                default_ide,
            )
            selected = default_ide
    _logger.info(
        _("You selected IDE configuration: {SELECTED_IDE}\n").format(
            SELECTED_IDE=selected,
        )
    )
    return selected
