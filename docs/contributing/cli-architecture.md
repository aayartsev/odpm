# Архитектура командной строки odpm

Как добавить новую user-facing команду или режим.

## Шаги

1. Константа в [`dev_project/host/cli/params.py`](../../dev_project/host/cli/params.py).
2. Файл `args_<verb>.py` — `register_*_subparser` с **узким** набором флагов (не сваливать всё в global parent). Глобально только `--version`/`-V`, секреты, security profile ([`args_global.py`](../../dev_project/host/cli/args_global.py)).
3. При необходимости поля в [`OdpmCliArgs`](../../dev_project/host/cli/args.py).
4. Mode-helper в [`dev_project/plan/cli.py`](../../dev_project/plan/cli.py) (`is_*_mode`).
5. Маршрутизация в [`OdpmPipeline.run`](../../dev_project/odpm_pipeline.py):
   - host tooling → early return + `*/commands.py`;
   - стек / runtime → prepare + `RuntimeCoordinator` (как `up`).
6. Если команда prepare-only — добавить в allowlist [`cli_allows_ci_explicit_mode`](../../dev_project/system_check_policy.py) и ADR-017.
7. Для стековых `database *` **не** класть логику в `database/commands.py` — выставлять legacy-поля флагов и идти в runtime path.
8. Docs RU (+ EN, если зеркало есть), CHANGELOG, тесты parse/normalize + dispatch.
9. Слой совместимости (`normalize_cli_args`) — только если нужен переход со старого argv; не плодить новые корневые mode-флаги.

## Host vs stack `database`

| Подкоманда | Путь |
|------------|------|
| `status`, `ensure-role`, `pull` | Early exit, лёгкий `setup(for_plan=True)` |
| `backup`, `restore`, `drop`, `list` | Полный setup + prepare + compose up + контейнер |

См. [ADR-026](adr-026-cli-command-verbs.md).
