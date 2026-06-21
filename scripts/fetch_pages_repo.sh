#!/usr/bin/env bash
# Download live APT or YUM repo tree from GitHub Pages (if published).
# Exits 0 even when nothing is live yet (fresh bootstrap).
set -euo pipefail

KIND="${1:?apt or yum}"
OUT="${2:?output directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${OUT}" != /* ]]; then
    OUT="${PROJECT_ROOT}/${OUT}"
fi

BASE="${PAGES_REPO_BASE:-https://aayartsev.github.io/odpm}"

mkdir -p "${OUT}"

case "${KIND}" in
    apt)
        if curl -fsSL "${BASE}/apt/dists/stable/Release" -o /tmp/odpm-apt-release 2>/dev/null || \
           curl -fsSL "${BASE}/apt/dists/testing/Release" -o /tmp/odpm-apt-release 2>/dev/null; then
            wget -q -r -np -nH --cut-dirs=2 -P "${OUT}" "${BASE}/apt/" || true
            echo "Fetched live APT repo into ${OUT}"
            find "${OUT}" -type f 2>/dev/null | sort | head -40 || true
            exit 0
        fi
        ;;
    yum)
        if curl -fsSL "${BASE}/yum/stable/repodata/repomd.xml" -o /tmp/odpm-yum-repomd 2>/dev/null || \
           curl -fsSL "${BASE}/yum/testing/repodata/repomd.xml" -o /tmp/odpm-yum-repomd 2>/dev/null; then
            wget -q -r -np -nH --cut-dirs=2 -P "${OUT}" "${BASE}/yum/" || true
            echo "Fetched live YUM repo into ${OUT}"
            find "${OUT}" -type f 2>/dev/null | sort | head -40 || true
            exit 0
        fi
        ;;
    *)
        echo "usage: fetch_pages_repo.sh apt|yum OUT_DIR" >&2
        exit 1
        ;;
esac

echo "No live ${KIND} repo on Pages yet; ${OUT} unchanged"
