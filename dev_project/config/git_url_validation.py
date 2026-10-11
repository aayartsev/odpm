"""Validate non-empty git URL strings in host config fields."""

from __future__ import annotations

from ..errors import ConfigError
from ..translations import _


def require_nonempty_git_url(value: object, *, field: str) -> str:
    """Return stripped URL or raise ConfigError when empty/whitespace."""
    text = "" if value is None else str(value).strip()
    if not text:
        raise ConfigError(
            _("Git repository URL for {FIELD} is empty").format(FIELD=field)
        )
    return text


def require_nonempty_dependency_urls(dependencies: object) -> list[str]:
    """Validate host ``dependencies`` list; reject empty/whitespace entries."""
    if not isinstance(dependencies, list):
        return []
    validated: list[str] = []
    for index, item in enumerate(dependencies):
        if item is None:
            raise ConfigError(
                _("Git repository URL for {FIELD} is empty").format(
                    FIELD=f"dependencies[{index}]"
                )
            )
        text = str(item).strip()
        if not text:
            raise ConfigError(
                _("Git repository URL for {FIELD} is empty").format(
                    FIELD=f"dependencies[{index}]"
                )
            )
        validated.append(text)
    return validated
