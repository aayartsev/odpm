# odpm tools by scenario

> **AI-translated** from Russian.

A single odpm utility provides a **set of commands**; in different scenarios (`ODPM_SCENARIO`) some of them do not apply or behave differently.

| Task | Developer | Server | Image build |
|------|:---------:|:------:|:-----------:|
| Initialization `odpm init` | yes | yes | yes |
| Prepare `odpm prepare` / `odpm up` | yes | yes | `prepare` yes; `up` **forbidden** (ADR-017) |
| Start stack | `odpm up` / `docker compose up` | yes | `docker compose` only after `prepare` / `build` |
| Database and modules `odpm up -d -i -u` | yes | yes | after `compose up` via `compose exec` (not `odpm up`) |
| Module tests `-t` (on `up`) | yes | rarely | yes |
| Backup / restore (`odpm database …` / `odpm up --db-*`) | yes | yes | stack `database` **forbidden** in ci |
| Admin password change, translations | yes | yes | as needed |
| Module scaffold `scaffold` | yes | no | **forbidden** in ci |
| VS Code debugging | yes | no | no |
| Module secrets (`--secrets-file`, `/run/odpm/secrets.json`) | yes | yes | no (host mount) |
| Run pre-commit in container | yes | no | no |
| Change plan `odpm plan` | yes | yes | yes |
| Lock update `odpm prepare --update-lock` | coordinator | read | strict |
| Image build `odpm build` | **no** | **no** | **yes** |
| Backend `--image-builder` / env `ODPM_CI_IMAGE_BUILDER` (`docker`, `kaniko`) | **no** | **no** | **yes** |
| Publish `--image-push` / env `ODPM_CI_IMAGE_PUSH` | **no** | **no** | **yes** |
| Prepare without git `--no-git-update` | yes | yes | yes |

Full parameter list: [command line](cli.md). For `kaniko` see [ci scenario](../scenarios/ci.md) and [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md).
