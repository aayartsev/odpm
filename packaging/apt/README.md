# APT repository (GitHub Pages)

Signed static APT repo published at `https://aayartsev.github.io/odpm/apt/`.

| File | In git | Purpose |
|------|--------|---------|
| `odpm-archive-keyring.gpg` | yes (maintainer) | Binary public keyring for APT `signed-by=` on GitHub Pages |
| `reprepro/conf/*` | yes | Repository layout (`stable`, `testing`) |

Generate and commit the public keyring once:

```bash
gpg --armor --export KEYID | gpg --dearmor > packaging/apt/odpm-archive-keyring.gpg
```

## User install

See [docs/install/README.md](../../docs/install/README.md) (hub) and [linux-deb.md](../../docs/install/linux-deb.md). Keyring on the user's machine:

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg \
  -o /usr/share/keyrings/odpm-archive-keyring.gpg
```

## Maintainer secrets (GitHub Actions)

| Secret | Content |
|--------|---------|
| `APT_REPO_GPG_PRIVATE_KEY` | Armored **private** key (`gpg --armor --export-secret-keys`) |
| `APT_REPO_GPG_PASSPHRASE` | Passphrase set when the key was generated |

Do **not** commit the private key.

## Local smoke

```bash
export APT_REPO_GPG_PRIVATE_KEY="$(gpg --armor --export-secret-keys KEYID)"
export APT_REPO_GPG_PASSPHRASE='...'
./scripts/build_deb.sh
./scripts/import_apt_signing_key.sh
./scripts/build_apt_repo.sh testing dist/odpm_*.deb /tmp/odpm-apt
find /tmp/odpm-apt -type f
```

## Suites

| Release tag | APT suite |
|-------------|-----------|
| Stable (`v4.3.0`) | `stable` |
| Pre-release (`v4.3-rc1`, `*-beta`) | `testing` |
