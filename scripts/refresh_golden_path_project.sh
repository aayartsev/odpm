#!/usr/bin/env bash
# Refresh long-lived ODPM_GOLDEN_PATH_PROJECT before golden-path CI (release-packages).
set -euo pipefail

PROJECT="${ODPM_GOLDEN_PATH_PROJECT:?Set ODPM_GOLDEN_PATH_PROJECT}"

if [[ ! -d "${PROJECT}" ]]; then
    echo "ODPM_GOLDEN_PATH_PROJECT is not a directory: ${PROJECT}" >&2
    exit 1
fi

if [[ ! -f "${PROJECT}/docker-compose.yml" ]]; then
    echo "Missing docker-compose.yml in ${PROJECT}" >&2
    exit 1
fi

cd "${PROJECT}"
docker compose down --remove-orphans 2>/dev/null || true

if ! command -v odpm >/dev/null 2>&1; then
    echo "odpm not found on PATH; install the built .deb before refresh" >&2
    exit 1
fi

odpm --skip-start --no-git-update

echo "Golden-path project refreshed with $(odpm --version 2>&1 | head -1)"
