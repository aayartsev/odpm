#!/usr/bin/env bash
# Check out docs/ + mkdocs.yml from a release tag, add version hub/overrides from dev branch,
# patch mkdocs for mike, and verify nav paths exist (bootstrap docs workflow).
set -euo pipefail

TAG="${1:?release tag (e.g. v4.3.0)}"
DEV_REF="${2:-4.4-dev}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [[ "${TAG}" != v* ]]; then
    TAG="v${TAG}"
fi

echo "Preparing bootstrap docs from ${TAG} (tooling from ${DEV_REF})"

git checkout "${TAG}" -- docs/ mkdocs.yml

restore_path() {
    local path="$1"
    if git cat-file -e "${DEV_REF}:${path}" 2>/dev/null; then
        git checkout "${DEV_REF}" -- "${path}"
    elif [[ -f "${path}" ]]; then
        echo "Using existing ${path} (not yet on ${DEV_REF})"
    else
        echo "Missing ${path} on ${DEV_REF} and in working tree" >&2
        exit 1
    fi
}

restore_path docs/getting-started/documentation-versions.md
restore_path docs/en/getting-started/documentation-versions.md
restore_path docs/overrides/main.html

python3 "${SCRIPT_DIR}/patch_mkdocs_bootstrap.py" mkdocs.yml

echo "Bootstrap docs tree ready; nav validated against docs/"
