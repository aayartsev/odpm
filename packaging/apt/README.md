# APT repository (GitHub Pages)

Signed static APT repo published at `https://aayartsev.github.io/odpm/apt/`.

Release policy (stable vs testing, bootstrap, checklists): [docs/contributing/release-lines.md](../../docs/contributing/release-lines.md). CI details: [docs/contributing/packaging.md](../../docs/contributing/packaging.md).

| File | In git | Purpose |
|------|--------|---------|
| `odpm-archive-keyring.gpg` | yes (maintainer) | Binary public keyring for APT `signed-by=` on GitHub Pages |
| `reprepro/conf/*` | yes | Repository layout (`stable`, `testing`) |

Generate and commit the public keyring once:

```bash
gpg --armor --export KEYID | gpg --dearmor > packaging/apt/odpm-archive-keyring.gpg
```

YUM/DNF repo publish derives `odpm-archive-keyring.asc` from this file at build time (`scripts/build_yum_repo.sh`).

## User install

See [docs/install/README.md](../../docs/install/README.md) (hub) and [linux-deb.md](../../docs/install/linux-deb.md). Keyring on the user's machine:

```bash
sudo curl -fsSL https://aayartsev.github.io/odpm/apt/odpm-archive-keyring.gpg \
  -o /usr/share/keyrings/odpm-archive-keyring.gpg
```

- [`scripts/build_apt_repo.sh`](../../scripts/build_apt_repo.sh): флаг `--merge` сохраняет другие suite при публикации pre-release.
- [`scripts/fetch_pages_repo.sh`](../../scripts/fetch_pages_repo.sh) + [`scripts/overlay_pages_repo.sh`](../../scripts/overlay_pages_repo.sh): скачать live repo с Pages и наложить новый suite.
- One-shot bootstrap stable: workflow **Bootstrap Pages repos** (`.github/workflows/bootstrap-pages-repos.yml`) — checkout `4.4-dev`, скачивает `.deb`/`.rpm` с GitHub Release (input `v4.3.0`).
- One-shot bootstrap docs: workflow **Bootstrap docs versions** — `prepare_bootstrap_docs.sh` (docs/ + mkdocs с тега, hub/overrides с `4.4-dev`, mike patch).

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
| Stable (`v4.3.0`, `v4.4.2`, …) | `stable` |
| Pre-release (`v4.4.2-beta`, `*-rc`, `*-alpha`) | `testing` |

Stable and testing coexist on Pages: tag builds use `--merge` (see [release-lines.md](../../docs/contributing/release-lines.md)).
