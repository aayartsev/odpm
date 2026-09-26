"""YAML recipe loading and ${param.*} / ${env:VAR} substitution."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from ..translations import _
from ..yaml import load_document
from .types import OdpmStep, RecipeParam

_PARAM_RE = re.compile(r"\$\{param\.([A-Za-z_][A-Za-z0-9_]*)\}")
_ENV_RE = re.compile(r"\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def substitute_string(
    value: str,
    *,
    params: dict[str, str],
    environ: dict[str, str],
) -> str:
    def _param(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in params:
            raise ConfigError(
                _("Recipe substitution unknown param {NAME!r}.").format(NAME=key)
            )
        return params[key]

    def _env(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in environ or environ[key] is None:
            raise ConfigError(
                _("Recipe substitution missing env {NAME!r}.").format(NAME=key)
            )
        return str(environ[key])

    text = _PARAM_RE.sub(_param, value)
    return _ENV_RE.sub(_env, text)


def substitute_argv(
    argv: list[str],
    *,
    params: dict[str, str],
    environ: dict[str, str],
) -> list[str]:
    return [
        substitute_string(part, params=params, environ=environ) for part in argv
    ]


def parse_recipe_yaml(text: str, *, source: str = "<yaml>") -> dict[str, Any]:
    try:
        raw = load_document(text)
    except Exception as exc:  # noqa: BLE001 — surface as ConfigError
        raise ConfigError(
            _("Invalid recipe YAML in {PATH}: {ERROR}").format(PATH=source, ERROR=exc)
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigError(
            _("Recipe YAML root must be a mapping: {PATH}").format(PATH=source)
        )
    return raw


def load_recipe_yaml_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_recipe_yaml(text, source=str(path))


def recipe_params_from_yaml(raw: dict[str, Any]) -> list[RecipeParam]:
    params_raw = raw.get("params") or {}
    if not isinstance(params_raw, dict):
        raise ConfigError(_("Recipe 'params' must be a mapping."))
    out: list[RecipeParam] = []
    for name, spec in params_raw.items():
        if not isinstance(spec, dict):
            raise ConfigError(
                _("Recipe param {NAME!r} must be a mapping.").format(NAME=name)
            )
        out.append(
            RecipeParam(
                name=str(name),
                required=bool(spec.get("required", False)),
                env=str(spec["env"]).strip() if spec.get("env") else None,
                description=str(spec.get("description") or ""),
            )
        )
    return out


def recipe_steps_from_yaml(raw: dict[str, Any]) -> list[tuple[list[str], bool]]:
    """Return list of (argv_template, capture) before substitution."""
    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise ConfigError(_("Recipe 'steps' must be a non-empty list."))
    out: list[tuple[list[str], bool]] = []
    for index, step in enumerate(steps_raw):
        if not isinstance(step, dict) or "odpm" not in step:
            raise ConfigError(
                _("Recipe step {INDEX} must be a mapping with key 'odpm'.").format(
                    INDEX=index
                )
            )
        argv = step["odpm"]
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            raise ConfigError(
                _("Recipe step {INDEX} 'odpm' must be a list of strings.").format(
                    INDEX=index
                )
            )
        capture = bool(step.get("capture", False))
        out.append((list(argv), capture))
    return out


def materialize_yaml_step(
    argv_template: list[str],
    *,
    capture: bool,
    params: dict[str, str],
    environ: dict[str, str],
) -> OdpmStep:
    argv = substitute_argv(argv_template, params=params, environ=environ)
    return OdpmStep(
        argv=tuple(argv),
        capture=capture,
        timeout=120.0,
        execute_even_if_dry_run=False,
    )
