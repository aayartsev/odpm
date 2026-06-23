#!/usr/bin/env bash
# Deploy a MkDocs version with mike (--push to gh-pages), then materialize the site tree.
set -euo pipefail

VERSION="${1:?version directory name (e.g. dev, 4.3.0, 4.4.2-beta)}"
shift

ALIASES=()
TITLE=""
UPDATE_ALIASES=false
SET_DEFAULT=""
ALIAS_TYPE="${MIKE_ALIAS_TYPE:-copy}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --title)
            TITLE="${2:?}"
            shift 2
            ;;
        --update-aliases)
            UPDATE_ALIASES=true
            shift
            ;;
        --set-default)
            SET_DEFAULT="${2:?}"
            shift 2
            ;;
        --alias-type)
            ALIAS_TYPE="${2:?}"
            shift 2
            ;;
        --)
            shift
            ALIASES+=("$@")
            break
            ;;
        -*)
            echo "unknown option: $1" >&2
            exit 1
            ;;
        *)
            ALIASES+=("$1")
            shift
            ;;
    esac
done

if ! command -v mike >/dev/null 2>&1; then
    echo "mike not found; pip install -r requirements-docs.txt" >&2
    exit 1
fi

git fetch origin gh-pages --depth=1 2>/dev/null || true

MIKE_CMD=(mike deploy --push --alias-type "${ALIAS_TYPE}")
if [[ -n "${TITLE}" ]]; then
    MIKE_CMD+=(-t "${TITLE}")
fi
if [[ "${UPDATE_ALIASES}" == true ]]; then
    MIKE_CMD+=(--update-aliases)
fi
MIKE_CMD+=("${VERSION}")
if [[ "${#ALIASES[@]}" -gt 0 ]]; then
    MIKE_CMD+=("${ALIASES[@]}")
fi

echo "+ ${MIKE_CMD[*]}"
"${MIKE_CMD[@]}"

if [[ -n "${SET_DEFAULT}" ]]; then
    echo "+ mike set-default --push ${SET_DEFAULT}"
    mike set-default --push "${SET_DEFAULT}"
fi

# mike --push updates origin/gh-pages; refresh local ref before materializing the tree.
git fetch origin gh-pages --force --depth=1

SITE_DIR="$(mktemp -d)"
git worktree add --detach "${SITE_DIR}" origin/gh-pages

INSTALL_INDEX="${SITE_DIR}/${VERSION}/install/linux-deb/index.html"
if [[ ! -f "${INSTALL_INDEX}" ]]; then
    echo "missing docs tree after mike deploy: ${INSTALL_INDEX}" >&2
    ls -la "${SITE_DIR}/${VERSION}/install/" 2>/dev/null || ls -la "${SITE_DIR}/" >&2 || true
    exit 1
fi

echo "SITE_DIR=${SITE_DIR}"
