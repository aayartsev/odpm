"""IDE selection helpers from ODPM_IDE."""

from __future__ import annotations

from .constants import (
    ODPM_IDE_BOTH,
    ODPM_IDE_PYCHARM,
    ODPM_IDE_VSCODE,
)


def ide_includes_vscode(ide: str) -> bool:
    return ide in (ODPM_IDE_VSCODE, ODPM_IDE_BOTH)


def ide_includes_pycharm(ide: str) -> bool:
    return ide in (ODPM_IDE_PYCHARM, ODPM_IDE_BOTH)
