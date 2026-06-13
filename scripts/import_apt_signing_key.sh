#!/usr/bin/env bash
set -euo pipefail

: "${APT_REPO_GPG_PRIVATE_KEY:?APT_REPO_GPG_PRIVATE_KEY is required}"
: "${APT_REPO_GPG_PASSPHRASE:?APT_REPO_GPG_PASSPHRASE is required}"

GNUPGHOME="${GNUPGHOME:-${HOME}/.gnupg}"
mkdir -p "${GNUPGHOME}"
chmod 700 "${GNUPGHOME}"

if ! grep -q '^pinentry-mode loopback$' "${GNUPGHOME}/gpg.conf" 2>/dev/null; then
    echo "pinentry-mode loopback" >> "${GNUPGHOME}/gpg.conf"
fi
if ! grep -q '^allow-loopback-pinentry$' "${GNUPGHOME}/gpg-agent.conf" 2>/dev/null; then
    echo "allow-loopback-pinentry" >> "${GNUPGHOME}/gpg-agent.conf"
fi

gpg --batch --yes --pinentry-mode loopback \
    --passphrase "${APT_REPO_GPG_PASSPHRASE}" \
    --import <<< "${APT_REPO_GPG_PRIVATE_KEY}"

KEY_ID="$(
    gpg --list-secret-keys --keyid-format=long |
        awk '/^sec/ { sub(/.*\//, "", $2); print $2; exit }'
)"
if [[ -z "${KEY_ID}" ]]; then
    echo "No secret key found after import" >&2
    exit 1
fi

gpgconf --kill gpg-agent 2>/dev/null || true
gpgconf --launch gpg-agent

KEYGRIP="$(
    gpg --with-keygrip --list-secret-keys "${KEY_ID}" |
        awk '/Keygrip/ { print $3; exit }'
)"
if [[ -z "${KEYGRIP}" ]]; then
    echo "No keygrip for signing key ${KEY_ID}" >&2
    exit 1
fi

gpg-connect-agent --homedir "${GNUPGHOME}" \
    "PRESET_PASSPHRASE ${KEYGRIP} -1 ${APT_REPO_GPG_PASSPHRASE}" /bye >/dev/null

gpg --batch --pinentry-mode loopback \
    --passphrase "${APT_REPO_GPG_PASSPHRASE}" \
    --local-user "${KEY_ID}" \
    --clearsign <<< "odpm-apt-signing-smoke" >/dev/null

echo "Imported APT signing key ${KEY_ID} (gpg-agent preset OK)"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "key_id=${KEY_ID}" >> "${GITHUB_OUTPUT}"
fi
