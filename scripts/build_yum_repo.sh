#!/usr/bin/env bash
set -euo pipefail

SUITE="${1:?suite (stable|testing)}"
RPM="${2:?path to .rpm}"
OUT="${3:-yum-repo-out}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${OUT}" != /* ]]; then
    OUT="${PROJECT_ROOT}/${OUT}"
fi

if [[ ! -f "${RPM}" ]]; then
    echo "rpm not found: ${RPM}" >&2
    exit 1
fi

if [[ "${RPM}" != /* ]]; then
    RPM="${PROJECT_ROOT}/${RPM}"
fi
RPM="$(readlink -f "${RPM}")"
if [[ ! -f "${RPM}" ]]; then
    echo "rpm not found after resolve: ${RPM}" >&2
    exit 1
fi

KEYRING="${PROJECT_ROOT}/packaging/apt/odpm-archive-keyring.gpg"
if [[ ! -f "${KEYRING}" ]]; then
    echo "missing public keyring: ${KEYRING}" >&2
    exit 1
fi

if ! command -v createrepo_c >/dev/null 2>&1; then
    echo "createrepo_c not found; install: apt install createrepo-c  # or dnf install createrepo_c" >&2
    exit 1
fi

if ! command -v rpmsign >/dev/null 2>&1; then
    echo "rpmsign not found; install: apt install rpm  # or dnf install rpm-sign" >&2
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

RPMMACROS="${HOME}/.rpmmacros"
cat > "${RPMMACROS}" <<EOF
%_signature gpg
%_gpg_name ${KEY_ID}
%__gpg $(command -v gpg)
EOF

SIGNED_RPM="$(mktemp --suffix=.rpm)"
trap 'rm -f "${SIGNED_RPM}"' EXIT
cp "${RPM}" "${SIGNED_RPM}"
rpmsign --addsign "${SIGNED_RPM}"

rm -rf "${OUT}"
mkdir -p "${OUT}/${SUITE}/packages"
cp "${SIGNED_RPM}" "${OUT}/${SUITE}/packages/$(basename "${RPM}")"
cp "${KEYRING}" "${OUT}/odpm-archive-keyring.gpg"

createrepo_c --general-compress-types=gz "${OUT}/${SUITE}"
createrepo_c --update --general-compress-types=gz --gpg-sign "${KEY_ID}" "${OUT}/${SUITE}"

echo "YUM repo ready in ${OUT} (suite=${SUITE})"
find "${OUT}" -type f | sort
