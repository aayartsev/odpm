#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

export ODPM_SCENARIO="${ODPM_SCENARIO:-ci}"
if [[ "${ODPM_SCENARIO}" != "ci" ]]; then
    echo "ODPM_SCENARIO must be 'ci' (current: ${ODPM_SCENARIO})" >&2
    exit 1
fi

python3 "${PROJECT_ROOT}/odpm.py" --build-image
docker compose up -d

echo "CI image built; stack started with docker compose."
