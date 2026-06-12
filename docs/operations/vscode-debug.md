# VS Code и отладка

Отладка с точками останова доступна в сценарии **`developer`**.

## Что настраивает odpm

- В контейнере запускается **отладчик Python** (библиотека debugpy).
- На компьютер разработчика пробрасывается порт из **`DEBUGGER_PORT`** (по умолчанию 5678).
- В **`.odpm/runtime/debug-profile.json`** записывается **IDE-neutral профиль** (`schema_version: 2`): backend (`debugpy_listen`), direction (`attach`), protocol, host/port и `path_mappings` (локальный путь ↔ путь в контейнере). Файл в gitignore, как и `runtime/config.json`.
- По **`ODPM_IDE`** в `.env` odpm генерирует настройки IDE: **`vscode`** / **`both`** → `.vscode/launch.json` и `settings.json` (`VscodeConfigurator`); **`pycharm`** / **`both`** → `.run/Odoo Remote Attach.run.xml` (Attach to DAP, PyCharm 2024+); **`none`** — только `debug-profile.json`.

Пример фрагмента профиля:

```json
{
    "schema_version": 2,
    "debugger": {
        "backend": "debugpy_listen",
        "direction": "attach",
        "protocol": "debugpy",
        "host": "localhost",
        "port": 5678,
        "name": "Odoo: Remote Attach"
    },
    "path_mappings": [
        { "local": "/abs/path/on/host/odoo", "remote": "/home/odoo/odoo" }
    ]
}
```

Перегенерация: `odpm` или `odpm --skip-start` в сценарии **`developer`**. Шаг **`ide.debug_profile`** виден в `odpm plan`; с `--plan-show-diff` — diff для `debug-profile.json`.

## Порядок работы

1. Запустите Odoo через odpm (`odpm` или `odpm -d dev_db -u`).
2. В VS Code откройте панель «Выполнить и отладить» и подключитесь к конфигурации odpm.
3. Ставьте точки останова в файлах модулей.

## Символические ссылки для редактора (`create_module_links`)

Если в `user_settings.json` указано **`"create_module_links": true`**, odpm создаёт в корне проекта **символические ссылки** на каталоги platform, разрабатываемого проекта и зависимостей. Это упрощает навигацию и согласование путей в отладчике: в `launch.json` учитываются и реальные пути на диске (`~/odoo_projects/...`), и пути через ссылки в дереве каталога odpm-проекта.

По умолчанию опция **выключена**.

## На сервере и в сборке образа

В сценариях **`server`** и **`ci`** отладчик **не используется** — `debug-profile.json` и `.vscode/` не создаются. Не включайте `developer` на production ради отладки — для этого служит отдельная машина разработчика.

## PyCharm (Attach to DAP)

При `ODPM_IDE=pycharm` или `both` odpm создаёт **`.run/Odoo Remote Attach.run.xml`** — конфигурация **Attach to DAP** (PyCharm 2024+, поддержка debugpy). Запустите Odoo через odpm, откройте проект в PyCharm и подключитесь к конфигурации **Odoo: Remote Attach**.

**PyCharm Community Edition** не поддерживает remote debug; используйте VS Code/Cursor (`ODPM_IDE=vscode`) или PyCharm Professional.

Режим **PyCharm Debug Server** (`pydevd_connect`, контейнер подключается к IDE) — этап 2, только Professional.

## Другие IDE

| ID | Задача | Статус |
|----|--------|--------|
| TD-FEAT-08a | PyCharm Attach to DAP из `debug-profile.json` | реализовано (этап 1) |
| TD-FEAT-08b | PyCharm Debug Server + ручное подключение для прочих IDE | этап 2 / документация |
