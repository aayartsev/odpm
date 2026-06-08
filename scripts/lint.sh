#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if command -v ruff >/dev/null 2>&1; then
    exec ruff check dev_project tests odpm.py "$@"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv tool run ruff check dev_project tests odpm.py "$@"
fi

echo "ruff not found; install with: pip install ruff  (or: uv tool install ruff)" >&2
exit 1
