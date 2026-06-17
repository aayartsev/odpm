# Fedora / RHEL (.rpm)

Recommended on Fedora 41+.

## Install via DNF (`dnf upgrade` updates)

After a [release tag](https://github.com/aayartsev/odpm/releases), odpm publishes a signed repository on GitHub Pages.

### Repository key

Same GPG key as the APT repo (binary keyring on GitHub Pages). Verify after enabling the repo:

```bash
sudo rpm --import https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.gpg
sudo rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n' | grep -i odpm || true
# expected fingerprint: 03040028F53D7AB8  Alexander Yartsev
```

**Pre-release** (`v4.3-rc1`, `*-beta`) — suite **`testing`** (packages are here for now; `stable` after final releases):

```bash
sudo curl -fsSL https://raw.githubusercontent.com/aayartsev/odpm/main/packaging/yum/odpm-testing.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
```

**Stable releases** (`v4.3.0`, without `-rc`/`-beta`):

```bash
sudo curl -fsSL https://raw.githubusercontent.com/aayartsev/odpm/main/packaging/yum/odpm-stable.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
```

On RHEL / AlmaLinux / Rocky Linux use `yum` instead of `dnf` (same `.repo` format).

Updates on later releases:

```bash
sudo dnf makecache && sudo dnf upgrade odpm
```

Full install table for all platforms: [Installing odpm (all platforms)](README.md).

## Manual install (.rpm from GitHub Releases)

Download `odpm-*.rpm` from [GitHub Releases](https://github.com/aayartsev/odpm/releases), from **Actions → Release packages → Artifacts** (`release-packages`) after a push to `4.0-beta` / `4.0-rc1` / `main`, or build locally:

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

## Package dependencies

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Installs `/usr/bin/odpm` and `dev_project` under `python3/site-packages`.

When installing from GitHub Releases, verify checksums from the release `SHA256SUMS`.
