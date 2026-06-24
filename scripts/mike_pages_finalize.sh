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

mkdir -p "${SITE_DIR}/apt" "${SITE_DIR}/yum"
if [[ -n "${APT_SRC}" && -d "${APT_SRC}" ]]; then
    rsync -a "${APT_SRC}/" "${SITE_DIR}/apt/"
else
    "${SCRIPT_DIR}/fetch_pages_repo.sh" apt "${SITE_DIR}/apt" || true
fi
if [[ -n "${YUM_SRC}" && -d "${YUM_SRC}" ]]; then
    rsync -a "${YUM_SRC}/" "${SITE_DIR}/yum/"
else
    "${SCRIPT_DIR}/fetch_pages_repo.sh" yum "${SITE_DIR}/yum" || true
fi

PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Mike alias `stable` is a copy at /stable/; the version picker links to ./VERSION/
# relative to /stable/ → /stable/VERSION/ (404). Symlink to the real /VERSION/ tree.
fix_stable_version_picker_symlinks() {
    local site_dir="$1"
    local version
    version="$(
        grep '^LATEST_STABLE_RELEASE' "${PROJECT_ROOT}/dev_project/constants/scenarios.py" |
            sed -n 's/.*= "\([^"]*\)".*/\1/p'
    )"
    if [[ -z "${version}" ]]; then
        return 0
    fi
    if [[ ! -d "${site_dir}/stable" || ! -d "${site_dir}/${version}" ]]; then
        return 0
    fi
    local link="${site_dir}/stable/${version}"
    if [[ -e "${link}" && ! -L "${link}" ]]; then
        rm -rf "${link}"
    fi
    if [[ ! -e "${link}" ]]; then
        ln -sfn "../${version}" "${link}"
        echo "pages: symlink stable/${version} -> ../${version}"
    fi
}

fix_stable_version_picker_symlinks "${SITE_DIR}"

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
