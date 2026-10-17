# ADR-017: CI prepare-only policy

## Status

Accepted (4.7).

## Context

Сценарий `ci` historically мог дойти до `docker compose up` через bare `odpm`, требовал Docker daemon даже для prepare при Kaniko `direct`, и читал builder flags только из process `os.environ`, игнорируя layered `.env`. Нужен явный контракт: CI на build-runner — prepare / `--build-image`, без случайного compose up; daemonless path для `kaniko`+`direct`.

## Decision

1. **`SystemCheckPolicy`** расширен флагами:
   - `skip_docker_daemon` / `skip_compose_cli_probe` — `ci` + `kaniko` + `direct` + prepare-only (`--skip-start`, `--build-image`, `--update-lock` / `--sync-manifest-locks`, or `--init`);
   - `skip_ensure_base_local` — `ci` + `kaniko` (без `docker image inspect` / local ensure);
   - `relaxed_file_system` — `ci` + prepare-only (не требовать `BACKUP_DIR`);
   - `require_ci_explicit_mode` — `ci` (runtime guard);
   - `compose_validate` остаётся **всегда** on: structural YAML validate не отключается вместе с CLI probe.

2. **CI guard:** после `setup`, перед prepare, если `ODPM_SCENARIO=ci` и CLI не в allowlist → `ConfigError`. Allowlist: `prepare` / `--skip-start`, `build` / `--build-image`, `init` / `--init`, `plan` / `--plan`, `manifest`, `modules`, `run`, host-`database` (`status` / `ensure-role` / `pull`), `--update-lock` / `--sync-manifest-locks`, `-V` / `--version`. **Не** в allowlist: `up`, `scaffold`, stack-`database` (`backup` / `restore` / `drop` / `list`). Bare `odpm up -d/-i` и legacy root flags запрещены; module install — через `docker compose exec`. См. [ADR-026](adr-026-cli-command-verbs.md).

3. **Dotenv → resolve:** `resolve_ci_image_builder` / `push` получают merged environ (layered dotenv + process env, process wins) из `Config` / `HostProjectContext`.

4. **`check_docker` split:** `check_docker_daemon()` vs `ensure_base_image()`; каждый уважает соответствующие skip-флаги.

## Consequences

- Daemonless prepare на Kaniko `direct` не требует Docker daemon / compose CLI probe.
- Strict CI guard — breaking для docs/smoke, которые вызывали bare `odpm -d … -i` без skip.
- Wizard-значения builder в `.env` начинают влиять на policy и build (prerequisite для ADR-018/019).

## References

- [docs/scenarios/ci.md](../scenarios/ci.md)
- [docs/reference/env-dotenv.md](../reference/env-dotenv.md)
- ADR-016 (CI image build backends)
