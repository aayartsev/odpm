#!/usr/bin/env bash
# Overlay live and/or freshly built apt/yum repos onto a mike site tree (gh-pages root).
set -euo pipefail

SITE_DIR="${1:?mike site root (gh-pages worktree)}"
APT_SRC="${2:-}"
YUM_SRC="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${SITE_DIR}" != /* ]]; then
    SITE_DIR="$(cd "${SITE_DIR}" && pwd)"
fi

"${SCRIPT_DIR}/fetch_pages_repo.sh" apt "${SITE_DIR}/apt"
"${SCRIPT_DIR}/fetch_pages_repo.sh" yum "${SITE_DIR}/yum"

if [[ -n "${APT_SRC}" && -d "${APT_SRC}" ]]; then
    "${SCRIPT_DIR}/overlay_pages_repo.sh" apt "${SITE_DIR}/apt" "${APT_SRC}"
fi
if [[ -n "${YUM_SRC}" && -d "${YUM_SRC}" ]]; then
    "${SCRIPT_DIR}/overlay_pages_repo.sh" yum "${SITE_DIR}/yum" "${YUM_SRC}"
fi

echo "Pages site ready in ${SITE_DIR}"
find "${SITE_DIR}" -maxdepth 3 -type f 2>/dev/null | sort | head -60
