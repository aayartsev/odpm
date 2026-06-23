#!/usr/bin/env bash
# Verify live GitHub Pages after deploy-pages (versions.json + install index).
# OPS-02: fail CI on 404; retries absorb CDN lag after gh-pages push (OPS-01).
set -euo pipefail

BASE="${PAGES_REPO_BASE:-${ODPM_PAGES_BASE:-https://aayartsev.github.io/odpm}}"
VERSION=""
RETRIES="${ODPM_PAGES_VERIFY_RETRIES:-6}"
SLEEP="${ODPM_PAGES_VERIFY_SLEEP:-10}"

usage() {
    echo "usage: verify_pages_deploy.sh --version dev|stable|SEMVER [--base URL]" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base)
            BASE="${2:?}"
            shift 2
            ;;
        --version)
            VERSION="${2:?}"
            shift 2
            ;;
        -h | --help)
            usage
            ;;
        *)
            echo "unknown arg: $1" >&2
            usage
            ;;
    esac
done

[[ -n "${VERSION}" ]] || usage

BASE="${BASE%/}"
VERSION="${VERSION#/}"
INSTALL_URL="${BASE}/${VERSION}/install/linux-deb/"
VERSIONS_URL="${BASE}/versions.json"

check_once() {
    curl -fsSL "${VERSIONS_URL}" -o /tmp/odpm-versions.json
    python3 -c "import json; json.load(open('/tmp/odpm-versions.json'))"
    curl -fsSL -o /dev/null "${INSTALL_URL}"
    echo "OK: ${VERSIONS_URL}"
    echo "OK: ${INSTALL_URL}"
}

attempt=1
while [[ "${attempt}" -le "${RETRIES}" ]]; do
    echo "Pages verify attempt ${attempt}/${RETRIES} (base=${BASE}, version=${VERSION})"
    if check_once; then
        exit 0
    fi
    if [[ "${attempt}" -lt "${RETRIES}" ]]; then
        echo "Pages not ready yet; sleeping ${SLEEP}s..."
        sleep "${SLEEP}"
    fi
    attempt=$((attempt + 1))
done

echo "Pages verify failed after ${RETRIES} attempts (versions.json or install index)" >&2
exit 1
