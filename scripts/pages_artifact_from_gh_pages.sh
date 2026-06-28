#!/usr/bin/env bash
# Export origin/gh-pages into a clean directory for upload-pages-artifact (no .git worktree file).
set -euo pipefail

VERSION="${1:?version directory name to sanity-check (e.g. dev, 4.7.0-beta)}"

git fetch origin gh-pages --force --depth=1

SITE_DIR="$(mktemp -d)"
git archive --format=tar origin/gh-pages | tar -x -C "${SITE_DIR}"

if [[ ! -f "${SITE_DIR}/versions.json" ]]; then
    echo "missing versions.json on origin/gh-pages" >&2
    exit 1
fi

python3 -c "
import json, sys
want, root = sys.argv[1], sys.argv[2]
versions = json.load(open(f'{root}/versions.json'))
known = {e['version'] for e in versions}
aliases = {a for e in versions for a in e.get('aliases', [])}
if want not in known and want not in aliases:
    print(
        f'gh-pages versions.json missing {want!r}; '
        f'have versions={sorted(known)} aliases={sorted(aliases)}',
        file=sys.stderr,
    )
    sys.exit(1)
" "${VERSION}" "${SITE_DIR}"

INSTALL_INDEX="${SITE_DIR}/${VERSION}/install/linux-deb/index.html"
if [[ ! -f "${INSTALL_INDEX}" ]]; then
    echo "missing docs tree on gh-pages: ${INSTALL_INDEX}" >&2
    ls -la "${SITE_DIR}/${VERSION}/install/" 2>/dev/null || ls -la "${SITE_DIR}/" >&2 || true
    exit 1
fi

touch "${SITE_DIR}/.nojekyll"
echo "SITE_DIR=${SITE_DIR}"
