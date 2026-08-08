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
5. **Kaniko и base image:** локальный `ensure_base_image()` для kaniko **не** вызывается; тег base (`odoo_image_name`) должен быть доступен Kaniko из registry.
6. **Вне скоупа:** Buildah/podman, бэкенд сборки base image, генерация K8s Job YAML.

### ImageBuildSpec

- `context_dir`, `dockerfile`, `tag`, `platform` (`linux/<arch>`), `push: bool`

### Kaniko launch

| Mode | Env | Поведение |
|------|-----|-----------|
| `docker-run` (default) | `ODPM_KANIKO_EXECUTOR_MODE` unset/`docker-run` | `docker run --rm` образа `ODPM_KANIKO_EXECUTOR_IMAGE` |
| `direct` | `direct` | бинарь `ODPM_KANIKO_EXECUTOR_BIN` (default `executor`) |

## Consequences

- Локальный и docker-based CI путь без изменений при default.
- Daemonless CI может использовать `kaniko` + `direct` + registry credentials.
- В `docker-run` + `--image-push` без `~/.docker/config.json` — fail-fast до запуска executor.
- Pin образа executor (`DEFAULT_KANIKO_EXECUTOR_IMAGE`) перекрывается `ODPM_KANIKO_EXECUTOR_IMAGE`.
- Opt-in Docker integration (`test_ci_image_build`) покрывает только бэкенд `docker`; `kaniko` — unit-тесты argv/режимов (`test_ci_image_build_backends`).
- Документация сценария `ci`, CLI/env и tools-by-scenario описывает флаги и ограничение base.

## References

- [docs/scenarios/ci.md](../scenarios/ci.md)
- [docs/reference/cli.md](../reference/cli.md)
- [docs/reference/tools-by-scenario.md](../reference/tools-by-scenario.md)
- `dev_project/project_env/image_build/`
