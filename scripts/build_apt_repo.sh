#!/usr/bin/env bash
set -euo pipefail

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

rm -rf "${OUT}"
mkdir -p "${OUT}/conf"
cp "${PROJECT_ROOT}/packaging/apt/reprepro/conf/"* "${OUT}/conf/"
sed -i "s/%%GPG_KEY_ID%%/${KEY_ID}/g" "${OUT}/conf/distributions"
cp "${KEYRING}" "${OUT}/odpm-archive-keyring.gpg"

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
cd "${OUT}"
reprepro includedeb "${SUITE}" "${DEB}"
reprepro export "${SUITE}"

echo "APT repo ready in ${OUT} (suite=${SUITE})"
find . -type f | sort
