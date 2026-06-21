#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if ! command -v rpmbuild >/dev/null 2>&1; then
    echo "rpmbuild not found; install: dnf install rpm-build python3-devel python3-setuptools python3-wheel" >&2
    exit 1
fi

eval "$(
    python3 -c '
import sys

from dev_project.constants import RELEASE_VERSION
from scripts.release_native_versions import rpm_version_and_release

try:
    version, release = rpm_version_and_release(RELEASE_VERSION)
except ValueError as exc:
    sys.exit(str(exc))
print(f"RPM_VERSION={version}")
print(f"RPM_RELEASE={release}")
'
)"

TARBALL="odpm-${RPM_VERSION}.tar.gz"
TOPDIR="${PROJECT_ROOT}/.rpmbuild"

rm -rf "${TOPDIR}"
mkdir -p "${TOPDIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p dist

git config --global --add safe.directory "${PROJECT_ROOT}" 2>/dev/null || true
git archive --format=tar.gz --prefix="odpm-${RPM_VERSION}/" -o "${TOPDIR}/SOURCES/${TARBALL}" HEAD

cp packaging/odpm.spec "${TOPDIR}/SPECS/odpm.spec"

rpmbuild -ba \
    --define "_topdir ${TOPDIR}" \
    --define "version ${RPM_VERSION}" \
    --define "release ${RPM_RELEASE}%{?dist}" \
    "${TOPDIR}/SPECS/odpm.spec" "$@"

cp -f "${TOPDIR}"/RPMS/noarch/odpm-"${RPM_VERSION}"-"${RPM_RELEASE}"*.noarch.rpm dist/
echo "Built: dist/$(basename "${TOPDIR}"/RPMS/noarch/odpm-"${RPM_VERSION}"-"${RPM_RELEASE}"*.noarch.rpm)"
