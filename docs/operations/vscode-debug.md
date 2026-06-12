# VS Code и отладка

Отладка с точками останова доступна в сценарии **`developer`**.

## Что настраивает odpm

- В контейнере запускается **отладчик Python** (библиотека debugpy).
- На компьютер разработчика пробрасывается порт из **`DEBUGGER_PORT`** (по умолчанию 5678).
- В **`.odpm/runtime/debug-profile.json`** записывается **IDE-neutral профиль** (`schema_version: 1`): параметры подключения debugpy и `path_mappings` (локальный путь ↔ путь в контейнере). Файл в gitignore, как и `runtime/config.json`.
- В каталоге `.vscode/` создаётся **`launch.json`** и **`settings.json`** — VS Code читает те же mappings из профиля через `VscodeConfigurator`.

Пример фрагмента профиля:

```json
{
    "schema_version": 1,
    "debugger": {
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

## Другие IDE (запланировано)

Профиль задуман как общий контракт для генераторов конфигурации IDE (не только VS Code):

| ID | Задача | Статус |
|----|--------|--------|
| TD-FEAT-08a | Генератор run/debug конфигурации **PyCharm** из `debug-profile.json` | запланировано |
| TD-FEAT-08b | Документация «подключение вручную» для IDE без генератора (пути из профиля) | запланировано |

Сейчас автоматически настраивается только VS Code (`launch.json` / `settings.json`).
