#!/usr/bin/env bash
# Mirror live APT/YUM repos from GitHub Pages into mkdocs site/ before deploy.
# wget -r does not work here (no directory listings on Pages); we fetch explicit paths.
set -euo pipefail

SITE_DIR="${1:-site}"
PAGES_BASE="${ODPM_PAGES_BASE:-https://aayartsev.github.io/odpm}"

download_url() {
    local url="$1"
    local dest="$2"
    mkdir -p "$(dirname "${dest}")"
    curl -fsSL "${url}" -o "${dest}"
}

download_url_optional() {
    local url="$1"
    local dest="$2"
    mkdir -p "$(dirname "${dest}")"
    curl -fsSL "${url}" -o "${dest}" 2>/dev/null
}

apt_paths_from_release() {
    local release_file="$1"
    awk '
        /^SHA256:/ { in_sum = 1; next }
        /^SHA512:/ { in_sum = 1; next }
        /^[A-Za-z][A-Za-z0-9_-]*:/ {
            if ($0 !~ /^(SHA256|SHA512):/) {
                in_sum = 0
            }
            next
        }
        in_sum && NF >= 3 { paths[$3] = 1 }
        END {
            for (path in paths) {
                print path
            }
        }
    ' "${release_file}" | sort
}

yum_repodata_paths_from_repomd() {
    local repomd_file="$1"
    python3 - "${repomd_file}" <<'PY'
import sys
import xml.etree.ElementTree as ET

tree = ET.parse(sys.argv[1])
root = tree.getroot()
ns = {"repo": "http://linux.duke.edu/metadata/repo"}
for data in root.findall("repo:data", ns):
    location = data.find("repo:location", ns)
    if location is not None and location.get("href"):
        print(f"repodata/{location.get('href')}")
PY
}

yum_package_paths_from_primary() {
    local repodata_dir="$1"
    python3 - "${repodata_dir}" <<'PY'
import gzip
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

repodata = Path(sys.argv[1])
primary = None
for path in repodata.glob("primary.xml*"):
    if path.suffix == ".gz":
        primary = path
        break
if primary is None:
    plain = repodata / "primary.xml"
    if plain.is_file():
        primary = plain
if primary is None:
    raise SystemExit(0)

if str(primary).endswith(".gz"):
    with gzip.open(primary, "rb") as fh:
        tree = ET.parse(fh)
else:
    tree = ET.parse(primary)

root = tree.getroot()
ns = {"common": "http://linux.duke.edu/metadata/common"}
for pkg in root.findall("common:package", ns):
    location = pkg.find("common:location", ns)
    if location is not None and location.get("href"):
        print(location.get("href"))
PY
}

preserve_apt_repo() {
    local apt_base="${PAGES_BASE}/apt"
    local dest_root="${SITE_DIR}/apt"
    local found_suite=0
    local preserved_any=0

    for suite in stable testing; do
        local release_tmp
        release_tmp="$(mktemp)"
        if ! curl -fsSL "${apt_base}/dists/${suite}/Release" -o "${release_tmp}" 2>/dev/null; then
            rm -f "${release_tmp}"
            continue
        fi
        found_suite=1
        echo "Preserving APT suite ${suite} from ${apt_base}"

        download_url "${apt_base}/dists/${suite}/Release" "${dest_root}/dists/${suite}/Release"
        preserved_any=1

        mapfile -t rel_paths < <(apt_paths_from_release "${release_tmp}")
        rm -f "${release_tmp}"

        local rel_path
        for rel_path in "${rel_paths[@]}"; do
            [[ -n "${rel_path}" ]] || continue
            download_url "${apt_base}/${rel_path}" "${dest_root}/${rel_path}"
            preserved_any=1
        done

        for rel_path in "dists/${suite}/InRelease" "dists/${suite}/Release.gpg"; do
            if download_url_optional "${apt_base}/${rel_path}" "${dest_root}/${rel_path}"; then
                preserved_any=1
            fi
        done
    done

    if [[ "${found_suite}" -eq 0 ]]; then
        echo "No live APT repo on Pages; skipping preserve"
        return 0
    fi

    if download_url_optional "${apt_base}/odpm-archive-keyring.gpg" \
        "${dest_root}/odpm-archive-keyring.gpg"; then
        preserved_any=1
    fi

    if [[ "${preserved_any}" -eq 0 ]] || {
        [[ ! -f "${dest_root}/dists/stable/Release" ]] &&
            [[ ! -f "${dest_root}/dists/testing/Release" ]]
    }; then
        echo "APT preserve failed: live repo detected but files were not mirrored" >&2
        exit 1
    fi

    echo "Preserved APT repo under ${dest_root}"
    find "${dest_root}" -type f | sort | head -40
}

preserve_yum_repo() {
    local yum_base="${PAGES_BASE}/yum"
    local dest_root="${SITE_DIR}/yum"
    local found_suite=0

    download_url_optional "${yum_base}/odpm-archive-keyring.asc" \
        "${dest_root}/odpm-archive-keyring.asc" || true

    for suite in stable testing; do
        local repomd_tmp
        repomd_tmp="$(mktemp)"
        if ! curl -fsSL "${yum_base}/${suite}/repodata/repomd.xml" -o "${repomd_tmp}" 2>/dev/null; then
            rm -f "${repomd_tmp}"
            continue
        fi
        found_suite=1
        echo "Preserving YUM suite ${suite} from ${yum_base}"

        download_url "${yum_base}/${suite}/repodata/repomd.xml" \
            "${dest_root}/${suite}/repodata/repomd.xml"

        download_url_optional "${yum_base}/${suite}/repodata/repomd.xml.asc" \
            "${dest_root}/${suite}/repodata/repomd.xml.asc" || true

        mapfile -t repodata_paths < <(yum_repodata_paths_from_repomd "${repomd_tmp}")
        rm -f "${repomd_tmp}"

        local rel_path
        for rel_path in "${repodata_paths[@]}"; do
            [[ -n "${rel_path}" ]] || continue
            download_url "${yum_base}/${suite}/${rel_path}" \
                "${dest_root}/${suite}/${rel_path}"
        done

        mapfile -t package_paths < <(yum_package_paths_from_primary "${dest_root}/${suite}/repodata")

        for rel_path in "${package_paths[@]}"; do
            [[ -n "${rel_path}" ]] || continue
            download_url "${yum_base}/${suite}/${rel_path}" \
                "${dest_root}/${suite}/${rel_path}"
        done
    done

    if [[ "${found_suite}" -eq 0 ]]; then
        echo "No live YUM repo on Pages; skipping preserve"
        return 0
    fi

    if [[ ! -f "${dest_root}/stable/repodata/repomd.xml" ]] &&
        [[ ! -f "${dest_root}/testing/repodata/repomd.xml" ]]; then
        echo "YUM preserve failed: live repo detected but repomd.xml was not mirrored" >&2
        exit 1
    fi

    echo "Preserved YUM repo under ${dest_root}"
    find "${dest_root}" -type f | sort | head -40
}

main() {
    preserve_apt_repo
    preserve_yum_repo
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
