# YUM / DNF repository (GitHub Pages)

Signed static RPM repo published at `https://aayartsev.github.io/odpm/yum/`.

| File | In git | Purpose |
|------|--------|---------|
| `odpm-testing.repo` | yes | Example `.repo` for pre-releases (`testing` suite) |
| `odpm-stable.repo` | yes | Example `.repo` for stable releases |
| `odpm-archive-keyring.gpg` | no (copied at publish) | Same binary keyring as APT (`packaging/apt/odpm-archive-keyring.gpg`) |

## User install

See [docs/install/README.md](../../docs/install/README.md) (hub) and [fedora-rpm.md](../../docs/install/fedora-rpm.md).

## Maintainer secrets (GitHub Actions)

Same GPG key as the APT repo:

| Secret | Content |
|--------|---------|
| `APT_REPO_GPG_PRIVATE_KEY` | Armored **private** key (`gpg --armor --export-secret-keys`) |
| `APT_REPO_GPG_PASSPHRASE` | Passphrase set when the key was generated |

Do **not** commit the private key.

## Local smoke

```bash
export APT_REPO_GPG_PRIVATE_KEY="$(gpg --armor --export-secret-keys KEYID)"
export APT_REPO_GPG_PASSPHRASE='...'
./scripts/build_rpm.sh   # on Fedora, or use dist/*.rpm from CI
./scripts/import_apt_signing_key.sh
./scripts/build_yum_repo.sh testing dist/odpm-*.rpm /tmp/odpm-yum
find /tmp/odpm-yum -type f
```

Requires `createrepo_c`, `rpm` (`rpmsign`), and `gpg`.

## Suites

| Release tag | YUM suite |
|-------------|-----------|
| Stable (`v4.3.0`) | `stable` |
| Pre-release (`v4.3-rc1`, `*-beta`) | `testing` |
