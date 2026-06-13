#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RPM_GLOB="${1:-${PROJECT_ROOT}/dist/odpm-*.rpm}"
RPM_FILE="$(ls -1 ${RPM_GLOB} 2>/dev/null | head -1 || true)"

if [[ -z "${RPM_FILE}" ]]; then
    echo "No .rpm found (glob: ${RPM_GLOB}); run scripts/build_rpm.sh first" >&2
    exit 1
fi

if command -v rpmlint >/dev/null 2>&1; then
    rpmlint "${RPM_FILE}"
fi

dnf install -y "${RPM_FILE}"

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
print('rpm smoke OK:', templates)
"
