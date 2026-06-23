#!/usr/bin/env python3
"""Verify dev_project _('...') msgids are present in ru_RU catalog table."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_PROJECT = ROOT / "dev_project"
EN_US_PO = ROOT / "dev_project" / "i18n" / "en_US" / "LC_MESSAGES" / "main.po"


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
        is_gettext = isinstance(node.func, ast.Name) and node.func.id == "_"
        is_plan_msg = isinstance(node.func, ast.Name) and node.func.id == "plan_msg"
        if not (is_gettext or is_plan_msg):
            continue
        if len(node.args) != 1:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            msgids.add(arg.value)
    return msgids


def _collect_host_summary_msgids() -> set[str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import dev_project.host_summaries as host_summaries

    return {
        value
        for name, value in vars(host_summaries).items()
        if name.startswith("MSG_") and isinstance(value, str)
    }


def _count_po_msgids(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith('msgid "') and line != 'msgid ""'
    )


def main() -> int:
    catalog = _load_ru_messages()
    used: set[str] = set()
    for path in sorted(DEV_PROJECT.rglob("*.py")):
        if path.name == "translations.py":
            continue
        used |= _collect_msgids(path)
    used |= _collect_host_summary_msgids()

    missing = sorted(used - catalog)
    unused = sorted(catalog - used)
    en_us_ok = EN_US_PO.is_file() and _count_po_msgids(EN_US_PO) == len(catalog)

    if missing:
        print("Missing ru_RU translations for msgids used in code:", file=sys.stderr)
        for msgid in missing:
            print(f"  - {msgid!r}", file=sys.stderr)

    if not en_us_ok:
        print(
            f"en_US catalog incomplete: expected {len(catalog)} msgids in {EN_US_PO}",
            file=sys.stderr,
        )

    if unused:
        print("Catalog entries not referenced by _('...') or plan_msg('...') in dev_project/:")
        for msgid in unused:
            print(f"  - {msgid!r}")

    if missing or not en_us_ok:
        return 1
    print(f"OK: {len(used)} msgid(s) in code, ru_RU and en_US catalogs cover all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
