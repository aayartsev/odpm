#!/usr/bin/env bash
# Overlay a freshly built repo artifact onto an existing tree (preserves other suites).
set -euo pipefail

KIND="${1:?apt or yum}"
TARGET="${2:?destination directory}"
SOURCE="${3:?artifact directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${TARGET}" != /* ]]; then
    TARGET="${PROJECT_ROOT}/${TARGET}"
fi
if [[ "${SOURCE}" != /* ]]; then
    SOURCE="${PROJECT_ROOT}/${SOURCE}"
fi

case "${KIND}" in
    apt)
        mkdir -p "${TARGET}/pool" "${TARGET}/dists"
        if [[ -d "${SOURCE}/pool" ]]; then
            rsync -a "${SOURCE}/pool/" "${TARGET}/pool/"
        fi
        for suite in stable testing; do
            if [[ -d "${SOURCE}/dists/${suite}" ]]; then
                mkdir -p "${TARGET}/dists/${suite}"
                rsync -a "${SOURCE}/dists/${suite}/" "${TARGET}/dists/${suite}/"
            fi
        done
        if [[ -f "${SOURCE}/odpm-archive-keyring.gpg" ]]; then
            cp "${SOURCE}/odpm-archive-keyring.gpg" "${TARGET}/"
        fi
        ;;
    yum)
        mkdir -p "${TARGET}"
        if [[ -f "${SOURCE}/odpm-archive-keyring.asc" ]]; then
            cp "${SOURCE}/odpm-archive-keyring.asc" "${TARGET}/"
        fi
        for suite in stable testing; do
            if [[ -d "${SOURCE}/${suite}" ]]; then
                mkdir -p "${TARGET}/${suite}"
                rsync -a "${SOURCE}/${suite}/" "${TARGET}/${suite}/"
            fi
        done
        ;;
    *)
        echo "usage: overlay_pages_repo.sh apt|yum TARGET SOURCE" >&2
        exit 1
        ;;
esac

echo "Overlaid ${KIND} repo from ${SOURCE} onto ${TARGET}"
find "${TARGET}" -type f 2>/dev/null | sort
