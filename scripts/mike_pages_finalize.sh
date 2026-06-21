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

PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
for repo_file in odpm-stable.repo odpm-testing.repo; do
    if [[ -f "${PROJECT_ROOT}/packaging/yum/${repo_file}" ]]; then
        cp "${PROJECT_ROOT}/packaging/yum/${repo_file}" "${SITE_DIR}/yum/${repo_file}"
    fi
done

# upload-pages-artifact@v5+ include-hidden-files; touch anyway for gh-pages branch sync.
touch "${SITE_DIR}/.nojekyll"

if git -C "${SITE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    sync_paths=(.nojekyll)
    if [[ -f "${SITE_DIR}/apt/dists/stable/Release" || -f "${SITE_DIR}/apt/dists/testing/Release" ]]; then
        sync_paths+=(apt)
    fi
    if [[ -d "${SITE_DIR}/yum/stable" || -d "${SITE_DIR}/yum/testing" \
        || -f "${SITE_DIR}/yum/odpm-archive-keyring.asc" ]]; then
        sync_paths+=(yum)
    fi
    git -C "${SITE_DIR}" add -f "${sync_paths[@]}"
    if ! git -C "${SITE_DIR}" diff --staged --quiet; then
        git -C "${SITE_DIR}" commit -m "pages: sync package repos and .nojekyll"
        git -C "${SITE_DIR}" push origin HEAD:gh-pages
    fi
fi

echo "Pages site ready in ${SITE_DIR}"
find "${SITE_DIR}" -maxdepth 3 -type f 2>/dev/null | sort | head -60
