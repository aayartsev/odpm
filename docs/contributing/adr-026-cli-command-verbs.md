# ADR-026: CLI command verbs

## Status

Accepted (4.8).

## Context

Корневые mode-флаги (`--skip-start`, `--init`, `--build-image`, `--db-*`) и голый `odpm` смешивали режимы в одном argv, усложняли help и политику сценария `ci`. Нужны явные подкоманды при сохранении совместимости в 4.8.

## Decision

1. **Глаголы:** `up`, `prepare`, `init`, `build` плюс существующие `plan` / `database` / `modules` / `run` / `manifest` / `scaffold`.
2. **Host vs stack `database`:** `status` / `ensure-role` / `pull` — ранний выход на хосте; `backup` / `restore` / `drop` / `list` — prepare + compose up + контейнер (те же поля, что у `--db-*`).
3. **Комбо** restore+`-i`/`-u` и несколько stack-флагов — только `odpm up`.
4. **Слой совместимости 4.8:** голый / legacy флаги → нормализация в подкоманды + предупреждение. Приоритет: `init` > `build` > `prepare` > один stack-флаг → `database *` > `up`. Запрет: prepare/init/build + stack-db флаги.
5. **`setup(for_plan)`:** лёгкий setup только для host-tooling; стек / `up` / `scaffold` — полный.
6. **CI allowlist:** `prepare` / `build` / `init` / `plan` / `manifest` / `modules` / `run` / host-`database` / `--version`/`-V`. Запрещены `up`, `scaffold`, stack-`database`.
7. **Версия:** глобально `-V` и `--version` (`-v` не использовать).
8. **Голый `odpm`:**
   - **4.8:** предупреждение + поведение как `odpm up`;
   - **5.0:** справка по подкомандам, exit 0, без prepare/up.

## Consequences

- Пользователи и docs переходят на явные глаголы; legacy argv живёт до 5.0.
- ADR-017 allowlist уточняется по подкоманде `database`.

## Checklist for 5.0

- [ ] Удалить корневые mode-флаги и shim «голый → `up`».
- [ ] Голый `odpm` → справка, exit 0.
- [ ] Обновить docs: «без команды = справка».

## References

- [docs/reference/cli.md](../reference/cli.md)
- [docs/contributing/cli-architecture.md](cli-architecture.md)
- [ADR-017](adr-017-ci-prepare-only-policy.md)
