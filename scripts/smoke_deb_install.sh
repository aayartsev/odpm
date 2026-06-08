#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEB_GLOB="${1:-${PROJECT_ROOT}/dist/odpm_*.deb}"
DEB_FILE="$(ls -1 ${DEB_GLOB} 2>/dev/null | head -1 || true)"

if [[ -z "${DEB_FILE}" ]]; then
    echo "No .deb found (glob: ${DEB_GLOB}); run scripts/build_deb.sh first" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq lintian "${DEB_FILE}"
lintian "${DEB_FILE}"

if [[ "$(id -u)" -eq 0 ]]; then
    useradd -m -s /bin/bash odpm-smoke 2>/dev/null || true
    RUN_AS=(runuser -u odpm-smoke --)
else
    RUN_AS=()
fi

"${RUN_AS[@]}" odpm --version
"${RUN_AS[@]}" python3 -c "
from dev_project.program_dir import resolve_program_dir
from pathlib import Path
import dev_project.constants as c

resolved = resolve_program_dir()
templates = Path(resolved) / c.DEV_PROJECT_DIR / 'templates'
mo = Path(resolved) / c.DEV_PROJECT_DIR / 'i18n/ru_RU/LC_MESSAGES/main.mo'
assert templates.is_dir(), templates
assert mo.is_file(), mo
print('deb smoke OK:', templates)
"
