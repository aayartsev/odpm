#!/usr/bin/env bash
# Run mandatory HTTP smoke (minimal fixture + Mailpit compose up + HTTP 200).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ODPM_RUN_HTTP_SMOKE=1
export ODPM_HTTP_SMOKE_TIMEOUT="${ODPM_HTTP_SMOKE_TIMEOUT:-600}"
export ODPM_COMPOSE_SMOKE_TIMEOUT="${ODPM_COMPOSE_SMOKE_TIMEOUT:-900}"

cd "${REPO_ROOT}"
exec python3 -m unittest tests.integration.test_http_smoke -v "$@"
