# ADR-016: CI image build backends (docker + kaniko)

## Status

Accepted (4.7).

## Context

`odpm --build-image` (сценарий `ci`) готовит контекст и `Dockerfile.ci`, затем собирает финальный образ. До 4.7 вызов был жёстко привязан к `docker build`, что неудобно в Kubernetes/CI без Docker daemon. Нужен тот же prepare/Dockerfile и сменный executor сборки.

## Decision

1. **Общий prepare** — `prepare_ci_build_context` и `generate_ci_dockerfile` не зависят от бэкенда.
2. **Бэкенды** — `ImageBuildBackend.build(ImageBuildSpec)`:
   - `docker` (default) — `docker build` (+ опционально `docker push`);
   - `kaniko` — executor Kaniko (`docker-run` или `direct`).
3. **Выбор:** CLI `--image-builder` > env `ODPM_CI_IMAGE_BUILDER` > `docker`.
4. **Push:** CLI `--image-push` или env `ODPM_CI_IMAGE_PUSH=1|true|yes`.
   - docker: `docker push <tag>` после build;
   - kaniko: `--destination=<tag>` при push; иначе `--no-push --tar-path=…/odpm-ci-image.tar`.
5. **Kaniko и base image:** base собирается тем же `ImageBuildBackend`; при `kaniko` base **всегда** пушится в `ODPM_BASE_IMAGE_REGISTRY` (обязателен). См. [ADR-019](adr-019-kaniko-base-image-build.md).
6. **Вне скоупа:** Buildah/podman, генерация K8s Job YAML, CLI `--build-base-image`.

### ImageBuildSpec

- `context_dir`, `dockerfile`, `tag`, `platform` (`linux/<arch>`), `push: bool`

### Kaniko launch

| Mode | Env | Поведение |
|------|-----|-----------|
| `docker-run` (default) | `ODPM_KANIKO_EXECUTOR_MODE` unset/`docker-run` | `docker run --rm` образа `ODPM_KANIKO_EXECUTOR_IMAGE` |
| `direct` | `direct` | бинарь `ODPM_KANIKO_EXECUTOR_BIN` (default `executor`) |

### Privilege boundary (`direct`)

odpm **не** запускается от root (`cli.py` guard). Kaniko executor в `direct` часто требует привилегий (chroot, runtime dir). odpm только **spawn**’ит executor; elevation — явная настройка окружения:

| Env | Назначение |
|-----|------------|
| `ODPM_KANIKO_EXECUTOR_WRAPPER` | Префикс argv (скрипт или `sudo -n /path/to/wrapper.sh`); **рекомендуется** |
| `ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS` | Доп. флаги executor (напр. `--kaniko-dir=/tmp/kaniko`) |
| `ODPM_KANIKO_EXECUTOR_SUDO=1` | Opt-in: prepend `sudo -n` перед бинарём, если wrapper не задан; нужен passwordless sudo |

Preflight в `KanikoImageBuildBackend.validate_direct_launch()`: non-root + `direct` без wrapper/sudo → `PipelineError` с подсказкой до запуска executor.

## Consequences

- Локальный и docker-based CI путь без изменений при default.
- Daemonless CI может использовать `kaniko` + `direct` + registry credentials; для `direct` на non-root runner задайте `ODPM_KANIKO_EXECUTOR_WRAPPER` или `ODPM_KANIKO_EXECUTOR_SUDO=1` (см. privilege boundary выше).
- В `docker-run` + `--image-push` без `~/.docker/config.json` — fail-fast до запуска executor.
- Pin образа executor (`DEFAULT_KANIKO_EXECUTOR_IMAGE`) перекрывается `ODPM_KANIKO_EXECUTOR_IMAGE`.
- Opt-in Docker integration (`test_ci_image_build`) покрывает только бэкенд `docker`; `kaniko` — unit-тесты argv/режимов (`test_ci_image_build_backends`).
- Документация сценария `ci`, CLI/env и tools-by-scenario описывает флаги и ограничение base.

## References

- [docs/scenarios/ci.md](../scenarios/ci.md)
- [docs/reference/cli.md](../reference/cli.md)
- [docs/reference/tools-by-scenario.md](../reference/tools-by-scenario.md)
- `dev_project/project_env/image_build/`
