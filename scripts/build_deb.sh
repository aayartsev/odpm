#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if ! command -v dpkg-buildpackage >/dev/null 2>&1; then
    echo "dpkg-buildpackage not found; install: sudo apt install build-essential devscripts debhelper dh-python pybuild-plugin-pyproject" >&2
    exit 1
fi

# Bind-mounted CI trees need safe.directory before git (write_build_meta).
git config --global --add safe.directory "${PROJECT_ROOT}" 2>/dev/null || true

python3 "${SCRIPT_DIR}/write_build_meta.py" "${PROJECT_ROOT}"

mkdir -p dist
dpkg-buildpackage -us -uc -b "$@"
cp -f ../odpm_*.deb dist/
echo "Built: dist/$(basename ../odpm_*.deb)"
