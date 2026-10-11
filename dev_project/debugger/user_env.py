"""Resolve debugger settings from host user_env (including test mocks)."""

from __future__ import annotations

from typing import Any

from .constants import DEFAULT_DEBUGGER_BACKEND, DEFAULT_DEBUGGER_CONNECT_HOST
from .env_parsing import parse_debugger_connect_host, parse_debugger_suspend


def resolve_debugger_backend_id(user_env: Any) -> str:
    backend = getattr(user_env, "debugger_backend", None)
    if isinstance(backend, str) and backend:
        return backend
    return DEFAULT_DEBUGGER_BACKEND


def resolve_debugger_port(user_env: Any) -> int:
    from ..host.ports import effective_debugger_port  # noqa: PLC0415  # cycle-safe

    return effective_debugger_port(user_env)


def resolve_debugger_connect_host(user_env: Any) -> str:
    raw = getattr(user_env, "debugger_connect_host", None)
    if isinstance(raw, str) and raw.strip():
        return parse_debugger_connect_host(raw)
    return DEFAULT_DEBUGGER_CONNECT_HOST


def resolve_debugger_suspend(user_env: Any) -> bool:
    raw = getattr(user_env, "debugger_suspend", None)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return parse_debugger_suspend(raw)
    return False
