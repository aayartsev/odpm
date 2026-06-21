# Fedora / RHEL (.rpm)

Recommended on **Fedora 40+** (system Python ≥ 3.10). The YUM repo ships builds for Fedora 40, 41, and 44 (`fc40` / `fc41` / `fc44` in the RPM name). On EL9 / RHEL 9 the stock `python3` 3.9 is not supported — use pip/pipx or build the RPM on Fedora.

Full platform table: [Installing odpm (all platforms)](README.md) · docs: [stable](https://aayartsev.github.io/odpm/stable/en/install/fedora-rpm/).

## Install via DNF (`dnf upgrade` updates)

After a [release tag](https://github.com/aayartsev/odpm/releases), odpm publishes a signed repository on GitHub Pages (`https://aayartsev.github.io/odpm/yum/`).

### Repository key

Same GPG key as the APT repo; GitHub Pages publishes an **ASCII-armored** file (`.asc`) for RPM/DNF:

```bash
sudo rpm --import https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.asc
sudo rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n' | grep -i yartsev || true
# expected fingerprint: 03040028F53D7AB8  Alexander Yartsev
```

### Stable (recommended for production)

Suite **`stable`** — currently odpm **4.3.0**:

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/yum/odpm-stable.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
odpm --version
# expected: odpm version: 4.3.0
```

### Pre-release (4.4 beta / RC)

Suite **`testing`** — currently **4.4.2-beta** and other pre-release tags:

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/yum/odpm-testing.repo \
  -o /etc/yum.repos.d/odpm.repo

sudo dnf makecache
sudo dnf install odpm
```

4.4-specific docs: [4.4.2-beta install guide](https://aayartsev.github.io/odpm/4.4.2-beta/en/install/fedora-rpm/).

> If `odpm-archive-keyring.asc` is not on Pages yet after a release, import from the APT binary keyring:
>
> ```bash
> curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg -o /tmp/odpm-key.gpg
> gpg --no-default-keyring --keyring /tmp/odpm-key.gpg --export --armor | sudo rpm --import -
> ```

On RHEL / AlmaLinux / Rocky Linux use `yum` instead of `dnf` (same `.repo` format).

Updates on later releases:

```bash
sudo dnf makecache && sudo dnf upgrade odpm
```

## Manual install (.rpm from GitHub Releases)

Download `odpm-*.rpm` from [GitHub Releases](https://github.com/aayartsev/odpm/releases) for tag `v4.3.0` (stable) or `v4.4.2-beta` (testing), or build locally:

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

Verify checksums from the release `SHA256SUMS`.

## Package dependencies

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Installs `/usr/bin/odpm` and `dev_project` under `python3/site-packages`.

## Next

[Local dev from scratch](../getting-started/local-dev-from-scratch.md)
