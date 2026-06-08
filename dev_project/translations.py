"""Host CLI gettext catalog (stdlib only)."""

from __future__ import annotations

import gettext as _stdlib_gettext
import locale
import os
from typing import Callable

from . import constants

_PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
_I18N_DIR = os.path.join(_PROGRAM_DIR, "i18n")
_CATALOG_DOMAIN = "main"

_LANG_ALIASES = {
    "C": constants.DEFAULT_LOCALE,
    "POSIX": constants.DEFAULT_LOCALE,
    "en": "en_US",
    "ru": "ru_RU",
}


def _normalize_locale(value: str | None) -> str:
    if not value:
        return constants.DEFAULT_LOCALE
    base = value.split(".")[0].split("@")[0].replace("-", "_")
    return _LANG_ALIASES.get(base, base)


def _locale_from_environment() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(var)
        if raw:
            return _normalize_locale(raw)
    try:
        default = locale.getdefaultlocale()[0]
    except (AttributeError, ValueError, TypeError):
        default = None
    return _normalize_locale(default)


def _language_candidates(app_locale: str) -> list[str]:
    candidates: list[str] = []
    for value in (app_locale, _LANG_ALIASES.get(app_locale, "")):
        if value and value not in candidates:
            candidates.append(value)
    if "_" in app_locale:
        language = app_locale.split("_", 1)[0]
        alias = _LANG_ALIASES.get(language)
        for value in (language, alias):
            if value and value not in candidates:
                candidates.append(value)
    return candidates


class Translator:
    def __new__(cls) -> Translator:
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.app_locale = _locale_from_environment()
        self._gettext: Callable[[str], str] = self._identity_gettext
        self.set_locale()

    @staticmethod
    def _identity_gettext(message: str) -> str:
        return message

    def update_locale(self, app_locale: str) -> None:
        self.app_locale = _normalize_locale(app_locale)
        self.set_locale()

    def set_locale(self) -> None:
        try:
            locale.setlocale(locale.LC_ALL, "")
        except locale.Error:
            pass
        self.app_locale = _normalize_locale(
            self.app_locale or _locale_from_environment()
        )
        catalog = _stdlib_gettext.translation(
            _CATALOG_DOMAIN,
            localedir=_I18N_DIR,
            languages=_language_candidates(self.app_locale),
            fallback=True,
        )
        self._gettext = catalog.gettext

    def gettext(self, message: str) -> str:
        return self._gettext(message)


_translator = Translator()


def gettext(message: str) -> str:
    return _translator.gettext(message)


def update_locale(app_locale: str) -> None:
    _translator.update_locale(app_locale)


_ = gettext
