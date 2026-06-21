#!/usr/bin/env bash
set -euo pipefail

MERGE=false
if [[ "${1:-}" == "--merge" ]]; then
    MERGE=true
    shift
fi

SUITE="${1:?suite (stable|testing)}"
OUT="${2:?output directory}"
shift 2

if [[ $# -lt 1 ]]; then
    echo "usage: build_yum_repo.sh [--merge] SUITE OUT RPM [RPM...]" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${OUT}" != /* ]]; then
    OUT="${PROJECT_ROOT}/${OUT}"
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

if [[ "${MERGE}" == true && -d "${OUT}" ]]; then
    echo "YUM merge mode: preserving existing suites in ${OUT}"
else
    rm -rf "${OUT}"
    mkdir -p "${OUT}"
fi

mkdir -p "${OUT}/${SUITE}/packages"
# RPM/DNF expect an ASCII-armored public key; APT uses the binary keyring in packaging/apt/.
gpg --no-default-keyring --keyring "${KEYRING}" --export --armor \
    > "${OUT}/odpm-archive-keyring.asc"

for rpm_arg in "$@"; do
    RPM="${rpm_arg}"
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

    SIGNED_RPM="$(mktemp --suffix=.rpm)"
    cp "${RPM}" "${SIGNED_RPM}"
    rpmsign --addsign "${SIGNED_RPM}"
    cp "${SIGNED_RPM}" "${OUT}/${SUITE}/packages/$(basename "${RPM}")"
    rm -f "${SIGNED_RPM}"
done

createrepo_c "${OUT}/${SUITE}"

REPOMD="${OUT}/${SUITE}/repodata/repomd.xml"
gpg --batch --yes --pinentry-mode loopback \
    --passphrase "${APT_REPO_GPG_PASSPHRASE}" \
    --local-user "${KEY_ID}" \
    --detach-sign --armor \
    -o "${OUT}/${SUITE}/repodata/repomd.xml.asc" \
    "${REPOMD}"

if [[ "${MERGE}" == true ]]; then
    echo "YUM repo merged in ${OUT} (suite=${SUITE})"
else
    echo "YUM repo ready in ${OUT} (suite=${SUITE})"
fi
find "${OUT}" -type f | sort
