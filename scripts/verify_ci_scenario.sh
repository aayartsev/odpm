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

if [[ -n "${ODPM_CI_PROJECT:-}" ]]; then
    LOCK_FILE="${ODPM_CI_PROJECT}/.odpm/deps.lock.json"
    if [[ "${ODPM_SKIP_DEPS_LOCK_CHECK:-}" != "1" ]] && [[ ! -f "${LOCK_FILE}" ]]; then
        echo "Missing ${LOCK_FILE}; run odpm.py --update-lock in the project or set ODPM_SKIP_DEPS_LOCK_CHECK=1" >&2
        exit 1
    fi
    echo "Preparing project (lock checkout) in ${ODPM_CI_PROJECT} ..."
    (cd "${ODPM_CI_PROJECT}" && python3 "${PROJECT_ROOT}/odpm.py" --skip-start)
fi

python3 "${PROJECT_ROOT}/odpm.py" --build-image
docker compose up -d

ODOO_PORT="${ODOO_PORT:-8069}"
echo "Waiting for Odoo HTTP 200 on http://127.0.0.1:${ODOO_PORT}/web ..."
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${ODOO_PORT}/web" >/dev/null; then
    echo "CI image built; stack started; Odoo HTTP OK."
    exit 0
  fi
  sleep 5
done

echo "Timeout waiting for Odoo HTTP on port ${ODOO_PORT}" >&2
exit 1
