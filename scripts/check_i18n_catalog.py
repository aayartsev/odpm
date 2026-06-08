#!/usr/bin/env python3
"""Verify dev_project _('...') msgids are present in ru_RU catalog table."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_PROJECT = ROOT / "dev_project"


def _load_ru_messages() -> set[str]:
    spec = importlib.util.spec_from_file_location(
        "sync_i18n_catalog", ROOT / "scripts" / "sync_i18n_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.RU_MESSAGES)


def _collect_msgids(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    msgids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "_"):
            continue
        if len(node.args) != 1:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            msgids.add(arg.value)
    return msgids


def main() -> int:
    catalog = _load_ru_messages()
    used: set[str] = set()
    for path in sorted(DEV_PROJECT.rglob("*.py")):
        if path.name == "translations.py":
            continue
        used |= _collect_msgids(path)

    missing = sorted(used - catalog)
    unused = sorted(catalog - used)

    if missing:
        print("Missing ru_RU translations for msgids used in code:", file=sys.stderr)
        for msgid in missing:
            print(f"  - {msgid!r}", file=sys.stderr)

    if unused:
        print("Catalog entries not referenced by _('...') in dev_project/:")
        for msgid in unused:
            print(f"  - {msgid!r}")

    if missing:
        return 1
    print(f"OK: {len(used)} msgid(s) in code, ru_RU catalog covers all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
