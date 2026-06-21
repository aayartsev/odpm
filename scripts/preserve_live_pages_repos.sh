#!/usr/bin/env bash
# Snapshot live apt/yum trees from GitHub Pages before mike --push (best-effort).
set -euo pipefail

OUT_APT="${1:?apt preserve directory}"
OUT_YUM="${2:?yum preserve directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${OUT_APT}" "${OUT_YUM}"
"${SCRIPT_DIR}/fetch_pages_repo.sh" apt "${OUT_APT}" || true
"${SCRIPT_DIR}/fetch_pages_repo.sh" yum "${OUT_YUM}" || true

if [[ -f "${OUT_APT}/dists/stable/Release" || -f "${OUT_APT}/dists/testing/Release" ]]; then
    echo "Preserved live APT repo"
    find "${OUT_APT}" -type f 2>/dev/null | sort | head -20 || true
else
    echo "No live APT repo to preserve"
fi

if [[ -f "${OUT_YUM}/stable/repodata/repomd.xml" || -f "${OUT_YUM}/testing/repodata/repomd.xml" ]]; then
    echo "Preserved live YUM repo"
    find "${OUT_YUM}" -type f 2>/dev/null | sort | head -20 || true
else
    echo "No live YUM repo to preserve"
fi
