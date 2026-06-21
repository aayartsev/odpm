# Debian / Ubuntu (.deb)

Recommended on Linux. Full platform table: [Installing odpm (all platforms)](README.md) · docs: [stable](https://aayartsev.github.io/odpm/stable/en/install/linux-deb/).

## Install via APT (`apt upgrade` updates)

After a [release tag](https://github.com/aayartsev/odpm/releases), odpm publishes a signed repository on GitHub Pages (`https://aayartsev.github.io/odpm/apt/`).

### Repository key (once)

Binary keyring for `signed-by=` (ready for `/usr/share/keyrings/`):

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg \
  -o /usr/share/keyrings/odpm-archive-keyring.gpg
```

Verify:

```bash
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/odpm-archive-keyring.gpg \
  --list-keys
# expected: 03040028F53D7AB8  Alexander Yartsev
```

### Stable (recommended for production)

Suite **`stable`** — currently odpm **4.4.2** (tag `v4.4.2`, without `-rc`/`-beta`):

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt stable main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
odpm --version
# expected: odpm version: 4.4.2
```

### Pre-release (4.4 beta / RC)

Suite **`testing`** — pre-release tags (`*-beta`, `*-rc*`), e.g. **4.4.2-beta**:

```bash
echo 'deb [signed-by=/usr/share/keyrings/odpm-archive-keyring.gpg] https://aayartsev.github.io/odpm/apt testing main' | sudo tee /etc/apt/sources.list.d/odpm.list

sudo apt update
sudo apt install odpm
```

Archived 4.4 beta docs: [4.4.2-beta install guide](https://aayartsev.github.io/odpm/4.4.2-beta/en/install/linux-deb/).

Updates on later releases:

```bash
sudo apt update && sudo apt upgrade odpm
```

## Manual install (.deb from GitHub Releases)

Download `odpm_*_all.deb` from [GitHub Releases](https://github.com/aayartsev/odpm/releases) for the tag you need (`v4.4.2` — stable, `v4.4.2-beta` — testing), or build locally:

```bash
./scripts/build_deb.sh
sudo apt install ./dist/odpm_*_all.deb
odpm --version
```

Verify checksums from the release `SHA256SUMS`.

## Package dependencies

- **Depends:** `python3 (>= 3.10)`, `python3-packaging`, `git`
- **Recommends:** Docker (`docker.io` / `moby-engine`)
- No PyPI runtime dependencies

The package installs `/usr/bin/odpm`, templates, and i18n under `python3/dist-packages`.

## Next

[Local dev from scratch](../getting-started/local-dev-from-scratch.md)
