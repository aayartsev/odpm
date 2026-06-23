"""Test helpers for pinning host gettext locale."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from dev_project.translations import _translator, update_locale


@contextmanager
def host_locale(locale: str) -> Iterator[None]:
    previous = _translator.app_locale
    update_locale(locale)
    try:
        yield
    finally:
        update_locale(previous)
