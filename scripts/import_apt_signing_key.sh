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

echo "Imported APT signing key ${KEY_ID}"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "key_id=${KEY_ID}" >> "${GITHUB_OUTPUT}"
fi
