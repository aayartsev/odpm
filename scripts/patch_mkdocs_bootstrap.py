#!/usr/bin/env python3
"""Patch mkdocs.yml for bootstrap deploy: mike metadata, hub nav, path validation."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

HUB_NAV_TITLE = "Какую документацию читать"
HUB_NAV_PATH = "getting-started/documentation-versions.md"
HUB_NAV_TRANSLATION = "Which docs to read"
GETTING_STARTED = "С чего начать"


def _nav_entries(nav: list) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in nav:
        if isinstance(item, str):
            entries.append(("", item))
        elif isinstance(item, dict):
            for title, target in item.items():
                if isinstance(target, str):
                    entries.append((title, target))
                elif isinstance(target, list):
                    entries.extend(_nav_entries(target))
    return entries


def _insert_hub(nav: list) -> None:
    for item in nav:
        if not isinstance(item, dict) or GETTING_STARTED not in item:
            continue
        section = item[GETTING_STARTED]
        if not isinstance(section, list):
            return
        for entry in section:
            if isinstance(entry, dict) and entry.get(HUB_NAV_TITLE) == HUB_NAV_PATH:
                return
        section.insert(0, {HUB_NAV_TITLE: HUB_NAV_PATH})
        return


def _validate_nav(nav: list, docs_dir: Path) -> None:
    missing: list[str] = []
    for title, rel in _nav_entries(nav):
        path = docs_dir / rel
        if not path.is_file():
            missing.append(f"{title or rel}: {rel}")
    if missing:
        lines = "\n  ".join(missing)
        raise SystemExit(f"mkdocs nav references missing docs files:\n  {lines}")


def main() -> None:
    config_path = Path(sys.argv[1] if len(sys.argv) > 1 else "mkdocs.yml")
    project_root = config_path.resolve().parent
    docs_dir = project_root / "docs"

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    config["site_url"] = "https://aayartsev.github.io/odpm/stable/"
    config.setdefault("extra", {})
    config["extra"]["version"] = {
        "provider": "mike",
        "default": "stable",
        "alias": True,
    }
    config.setdefault("theme", {})
    config["theme"]["custom_dir"] = "docs/overrides"

    nav = config.get("nav")
    if not isinstance(nav, list):
        raise SystemExit("mkdocs.yml: nav must be a list")
    _insert_hub(nav)

    i18n = None
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and "i18n" in plugin:
            i18n = plugin["i18n"]
            break
    if i18n:
        languages = i18n.get("languages", [])
        for lang in languages:
            if lang.get("locale") == "en":
                translations = lang.setdefault("nav_translations", {})
                translations[HUB_NAV_TITLE] = HUB_NAV_TRANSLATION

    _validate_nav(nav, docs_dir)

    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
