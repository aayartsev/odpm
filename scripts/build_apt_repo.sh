#!/usr/bin/env bash
set -euo pipefail

MERGE=false
if [[ "${1:-}" == "--merge" ]]; then
    MERGE=true
    shift
fi

SUITE="${1:?suite (stable|testing)}"
DEB="${2:?path to .deb}"
OUT="${3:-apt-repo-out}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${OUT}" != /* ]]; then
    OUT="${PROJECT_ROOT}/${OUT}"
fi

if [[ ! -f "${DEB}" ]]; then
    echo "deb not found: ${DEB}" >&2
    exit 1
fi

if [[ "${DEB}" != /* ]]; then
    DEB="${PROJECT_ROOT}/${DEB}"
fi
DEB="$(readlink -f "${DEB}")"
if [[ ! -f "${DEB}" ]]; then
    echo "deb not found after resolve: ${DEB}" >&2
    exit 1
fi

KEYRING="${PROJECT_ROOT}/packaging/apt/odpm-archive-keyring.gpg"
if [[ ! -f "${KEYRING}" ]]; then
    echo "missing public keyring: ${KEYRING}" >&2
    exit 1
fi

KEY_ID="$(
    gpg --list-secret-keys --keyid-format=long |
        awk '/^sec/ { sub(/.*\//, "", $2); print $2; exit }'
)"
if [[ -z "${KEY_ID}" ]]; then
    echo "import signing key first (scripts/import_apt_signing_key.sh)" >&2
    exit 1
fi

GNUPGHOME="${GNUPGHOME:-${HOME}/.gnupg}"
if [[ -n "${APT_REPO_GPG_PASSPHRASE:-}" ]]; then
    KEYGRIP="$(
        gpg --with-keygrip --list-secret-keys "${KEY_ID}" |
            awk '/Keygrip/ { print $3; exit }'
    )"
    if [[ -n "${KEYGRIP}" ]]; then
        gpg-connect-agent --homedir "${GNUPGHOME}" \
            "PRESET_PASSPHRASE ${KEYGRIP} -1 ${APT_REPO_GPG_PASSPHRASE}" /bye >/dev/null
    fi
fi

export GPG_TTY="${GPG_TTY:-/dev/console}"

_build_into() {
    local target="${1:?}"
    local suite="${2:?}"
    local deb="${3:?}"

    rm -rf "${target}"
    mkdir -p "${target}/conf"
    cp "${PROJECT_ROOT}/packaging/apt/reprepro/conf/"* "${target}/conf/"
    sed -i "s/%%GPG_KEY_ID%%/${KEY_ID}/g" "${target}/conf/distributions"
    cp "${KEYRING}" "${target}/odpm-archive-keyring.gpg"

    cd "${target}"
    reprepro includedeb "${suite}" "${deb}"
    reprepro export "${suite}"
}

if [[ "${MERGE}" == true && -d "${OUT}/dists" ]]; then
    WORK="$(mktemp -d)"
    trap 'rm -rf "${WORK}"' EXIT
    _build_into "${WORK}" "${SUITE}" "${DEB}"
    mkdir -p "${OUT}/pool" "${OUT}/dists/${SUITE}"
    rsync -a "${WORK}/pool/" "${OUT}/pool/"
    rsync -a "${WORK}/dists/${SUITE}/" "${OUT}/dists/${SUITE}/"
    cp "${WORK}/odpm-archive-keyring.gpg" "${OUT}/"
    echo "APT repo merged into ${OUT} (suite=${SUITE}, preserved other suites)"
else
    _build_into "${OUT}" "${SUITE}" "${DEB}"
    echo "APT repo ready in ${OUT} (suite=${SUITE})"
fi

find "${OUT}" -type f | sort
