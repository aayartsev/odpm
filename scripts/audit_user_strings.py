#!/usr/bin/env python3
"""Inventory host-facing English literals not wrapped in gettext _().

Scans ``dev_project/`` excluding ``inside_docker_app/`` (container logs stay EN).
Use for Phase L coverage reviews; does not fail CI unless ``--fail-on-unwrapped``.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_PROJECT = ROOT / "dev_project"
SKIP_DIRS = frozenset({"inside_docker_app", "__pycache__"})


@dataclass(frozen=True)
class Finding:
    category: str
    path: Path
    line: int
    snippet: str


def _iter_python_files() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(DEV_PROJECT.rglob("*.py")):
        if path.name == "translations.py":
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        paths.append(path)
    return paths


def _is_gettext_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_"
    )


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def _audit_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    findings: list[Finding] = []
    rel = path.relative_to(ROOT)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "info",
            "warning",
            "error",
            "critical",
        }:
            msg = _first_string_arg(node)
            if msg is not None and not _is_gettext_call(node.args[0]):
                findings.append(
                    Finding(
                        "logger_literal",
                        rel,
                        getattr(node, "lineno", 0),
                        msg[:80],
                    )
                )
            continue

        if isinstance(node.func, ast.Name) and node.func.id == "ConfigError":
            msg = _first_string_arg(node)
            if msg is not None:
                findings.append(
                    Finding(
                        "config_error_literal",
                        rel,
                        getattr(node, "lineno", 0),
                        msg[:80],
                    )
                )
            continue

        if isinstance(node.func, ast.Name) and node.func.id == "PipelineError":
            msg = _first_string_arg(node)
            if msg is not None:
                findings.append(
                    Finding(
                        "pipeline_error_literal",
                        rel,
                        getattr(node, "lineno", 0),
                        msg[:80],
                    )
                )
            continue

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            for keyword in node.keywords:
                if keyword.arg != "help":
                    continue
                if isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, str
                ):
                    findings.append(
                        Finding(
                            "cli_help_literal",
                            rel,
                            getattr(node, "lineno", 0),
                            keyword.value.value[:80],
                        )
                    )

    return findings


def _collect_findings() -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_python_files():
        findings.extend(_audit_file(path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print category counts only",
    )
    parser.add_argument(
        "--fail-on-unwrapped",
        action="store_true",
        help="Exit 1 when any finding remains (opt-in strict gate)",
    )
    args = parser.parse_args()

    findings = _collect_findings()
    by_category: dict[str, list[Finding]] = {}
    for item in findings:
        by_category.setdefault(item.category, []).append(item)

    if args.summary:
        print("audit_user_strings summary (host dev_project/, excl. inside_docker_app):")
        for category in sorted(by_category):
            print(f"  {category}: {len(by_category[category])}")
        print(f"  total: {len(findings)}")
    else:
        for item in findings:
            print(f"{item.category}\t{item.path}:{item.line}\t{item.snippet!r}")

    if args.fail_on_unwrapped and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
