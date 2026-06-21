# odpm tools by scenario

> **AI-translated** from Russian.

A single odpm utility provides a **set of commands**; in different scenarios (`ODPM_SCENARIO`) some of them do not apply or behave differently.

| Task | Developer | Server | Image build |
|------|:---------:|:------:|:-----------:|
| Initialization `odpm --init` | yes | yes | yes |
| Prepare `odpm` / `--skip-start` | yes | yes | yes |
| Start `docker compose up` | yes | yes | yes |
| Database and modules `-d -i -u` | yes | yes | yes |
| Module tests `-t` | yes | rarely | yes |
| Database backup and restore | yes | yes | yes |
| Admin password change, translations | yes | yes | as needed |
| Module scaffold `scaffold` | yes | no | no |
| VS Code debugging | yes | no | no |
| Module secrets (`--secrets-file`, `/run/odpm/secrets.json`) | yes | yes | no |
| Run pre-commit in container | yes | no | no |
| Change plan `odpm plan` | yes | yes | yes |
| Lock update `--update-lock` | coordinator | read | strict |
| Image build `--build-image` | **no** | **no** | **yes** |
| Prepare without git `--no-git-update` | yes | yes | yes |

Full parameter list: [command line](cli.md).
