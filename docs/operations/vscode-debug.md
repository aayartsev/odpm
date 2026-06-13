# Отладка в IDE (VS Code, Cursor, PyCharm)

Отладка с точками останова доступна в сценарии **`developer`**. Режим задаётся **`ODPM_DEBUGGER_BACKEND`** в `.env` (см. [env-dotenv](../reference/env-dotenv.md)).

## Два режима (backends)

| Backend | Кто слушает порт | IDE | Compose |
|---------|------------------|-----|---------|
| **`debugpy_listen`** (по умолчанию) | контейнер (`debugpy --listen`) | VS Code / Cursor, PyCharm **Attach to DAP** | publish `DEBUGGER_PORT:DEBUGGER_PORT` |
| **`pydevd_connect`** | **IDE** (PyCharm Debug Server на хосте) | **только PyCharm Professional** | `extra_hosts: host.docker.internal:host-gateway`, **без** publish debugger-порта |

Семантика **`DEBUGGER_PORT`** зависит от backend:

- **`debugpy_listen`** — порт **в контейнере**, проброшенный на `localhost` на хосте (attach из IDE).
- **`pydevd_connect`** — порт **Debug Server на хосте** (PyCharm слушает `localhost:DEBUGGER_PORT`; контейнер подключается к `ODPM_DEBUGGER_CONNECT_HOST`).

## Что настраивает odpm

- В venv контейнера ставится пакет отладчика: **`debugpy`** или **`pydevd-pycharm`** (pin в `dev_project/constants/core.py`; при смене backend лишний пакет убирается из requirements).
- В **`.odpm/runtime/config.json`** — объект `debugger` (backend, port, connect_host, suspend_on_connect). Поля `connect_host` и `suspend_on_connect` записываются всегда; для `debugpy_listen` runtime их **не использует**.
- В **`.odpm/runtime/debug-profile.json`** — IDE-neutral профиль (`schema_version: 2`): `backend`, `direction`, `protocol`, host/port, `path_mappings`.
- По **`ODPM_IDE`**: `vscode` / `both` → `.vscode/`; `pycharm` / `both` → `.run/*.run.xml` (какой файл — зависит от backend); `none` — только `debug-profile.json`.

Перегенерация: `odpm` или `odpm --skip-start`. Шаги плана: `ide.debug_profile`, `pycharm.settings`; diff — `odpm plan --plan-show-diff`.

---

## `debugpy_listen` — VS Code / Cursor / PyCharm Attach to DAP

### Профиль (пример)

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

### Порядок работы (VS Code / Cursor)

1. `.env`: `ODPM_DEBUGGER_BACKEND=debugpy_listen`, `ODPM_IDE=vscode` (или `both`).
2. `odpm` — Odoo в контейнере слушает debugger-порт.
3. В VS Code: «Выполнить и отладить» → attach к конфигурации odpm.
4. Breakpoints в модулях.

### PyCharm Attach to DAP

При `ODPM_IDE=pycharm` или `both` и **`debugpy_listen`** odpm создаёт **`.run/Odoo Remote Attach.run.xml`** (Attach to DAP, PyCharm 2024+).

1. Запустите Odoo через odpm.
2. В PyCharm подключитесь к **Odoo: Remote Attach**.

**PyCharm Community Edition** не поддерживает remote debug в этом режиме — используйте VS Code/Cursor или PyCharm Professional.

---

## `pydevd_connect` — PyCharm Debug Server (Pro)

Контейнер **подключается к IDE**, а не наоборот. Требуется **PyCharm Professional** (Debug Server).

### Настройка `.env`

```ini
ODPM_DEBUGGER_BACKEND=pydevd_connect
ODPM_IDE=pycharm
DEBUGGER_PORT=5678
ODPM_DEBUGGER_CONNECT_HOST=host.docker.internal
ODPM_DEBUGGER_SUSPEND=1
```

- **`ODPM_IDE=vscode`** с `pydevd_connect` — несовместимо (odpm выдаёт warning); используйте `pycharm` или `both`.
- **`ODPM_IDE=none`** — XML не генерируется (warning); для Debug Server нужен `pycharm` / `both`.

Интерактивный wizard в `developer` спрашивает `connect_host` и `suspend` только при выборе `pydevd_connect`.

### Порядок работы (важен порядок шагов)

1. `odpm --skip-start` — директива обновит `docker-compose.yml`, `config.json`, **`.run/Odoo Debug Server.run.xml`**.
2. В PyCharm: **Run** (не Attach) конфигурацию **Odoo Debug Server** — в окне Debug: *Waiting for process connection...*
3. `odpm` или `docker compose up` — контейнер вызывает `pydevd_pycharm.settrace(connect_host, port, suspend=...)`.
4. При `ODPM_DEBUGGER_SUSPEND=1` — в PyCharm нажмите **Resume**, затем breakpoints в addon.

### Compose

- **Нет** строки `5678:5678` в `ports` у сервиса `odoo`.
- Есть **`extra_hosts: host.docker.internal:host-gateway`** (для Linux; на macOS Docker Desktop обычно работает и без ручной настройки).

### Профиль (пример)

```json
{
    "schema_version": 2,
    "debugger": {
        "backend": "pydevd_connect",
        "direction": "connect",
        "protocol": "pydevd",
        "host": "localhost",
        "port": 5678,
        "name": "Odoo: Remote Attach"
    },
    "path_mappings": [ ... ]
}
```

`host: localhost` в профиле — адрес, где **на хосте** слушает Debug Server (для PyCharm XML). Контейнер использует `connect_host` из `config.json` (обычно `host.docker.internal`).

### Ручное подключение (другие IDE / TD-FEAT-08b)

Для IDE без генератора odpm возьмите host/port из `debug-profile.json` и добавьте в процесс на стороне контейнера (после bootstrap venv):

```python
import pydevd_pycharm
pydevd_pycharm.settrace(
    "<connect_host>",
    port=<port>,
    suspend=<True|False>,
    stdout_to_server=True,
    stderr_to_server=True,
)
```

Пакет: `pydevd-pycharm` (версия pin в odpm, см. ниже).

---

## Смена backend

После смены `ODPM_DEBUGGER_BACKEND` выполните `odpm --skip-start` и перезапустите контейнеры.

При смене `ODPM_DEBUGGER_BACKEND` odpm при `odpm --skip-start` **удаляет** неактуальный odpm-файл (`.run/Odoo Remote Attach.run.xml` или `.run/Odoo Debug Server.run.xml`). Пользовательские конфигурации в `.run/` не затрагиваются.

При смене backend venv пересобирается с нужным pip-пакетом (`debugpy` ↔ `pydevd-pycharm`).

---

## Символические ссылки (`create_module_links`)

Если в `user_settings.json` указано **`"create_module_links": true`**, odpm создаёт симлинки на platform, developing project и зависимости. Это помогает согласовать пути в отладчике: в `launch.json` и PyCharm path mappings учитываются и `~/odoo_projects/...`, и пути через дерево odpm-проекта.

По умолчанию опция **выключена**.

## Импорты и анализ кода (Pylance / Pyright)

При `odpm --skip-start` (сценарий `developer`, `ODPM_IDE=vscode` или `both`) odpm генерирует `.vscode/settings.json` с **`python.analysis.extraPaths`** из того же графа репозиториев, что использует prepare:

- корень **platform** (`odoo_src_dir`);
- **developing** project;
- каждая **git-зависимость** из `dependencies_projects`;
- корни **subprojects** (монорепо с несколькими addon-каталогами);
- **venv** `site-packages`.

Если в каталоге проекта есть симлинки (`odoo`, `dependencies/<repo>`), в `extraPaths` попадают **относительные** пути workspace — удобнее для Cursor/VS Code.

Ограничения:

- **`odoo-stubs`** (сценарий **developer**, Odoo ≤ 18) ставится **автоматически** в `requirements_txt` — как `debugpy`. Источник: [odoo-ide/odoo-stubs](https://github.com/odoo-ide/odoo-stubs) (git-зависимость; для `pip install` нужен **git** на хосте). После пересоздания venv Pylance подхватит stubs из `site-packages` (уже в `extraPaths`). Для **Odoo ≥ 19** stubs не добавляются — в ядре встроен typing.
- Stubs покрывают **ядро** `odoo`, не `odoo.addons.*` (namespace addons создаётся в рантайме).
- Расширение [vscode-odoo](https://marketplace.visualstudio.com/items?itemName=trinhanhngoc.vscode-odoo) уже содержит свои stubs — дублирование безвредно.
- На **server** / **ci** `odoo-stubs` в `odpm.json` удаляется (как debugger-пакеты).
- файл **перезаписывается** при каждом `odpm --skip-start` — не правьте `extraPaths` вручную в `.vscode/settings.json`.

---

## Устранение неполадок

### Версия `pydevd-pycharm` и PyCharm

odpm использует **`pydevd-pycharm==243.25659.43`** (ориентир - PyCharm **2024.3**). При другой версии IDE возможны сбои подключения без явной ошибки. Сверьте версию PyCharm или подберите совместимую версию пакета в `"requirements_txt"` в файле `user_settings.json` (продвинутый сценарий).

### Linux: контейнер не достучится до хоста

Проверьте в `docker-compose.yml` наличие `extra_hosts: "host.docker.internal:host-gateway"`. При кастомном `ODPM_DEBUGGER_CONNECT_HOST` (IP хоста) `extra_hosts` может не добавляться — тогда укажите IP, доступный из контейнера.

### Odoo стартует до Debug Server

Используйте `ODPM_DEBUGGER_SUSPEND=1` и **сначала** запустите Debug Server в PyCharm, **затем** контейнер.

### Проверка без полноценного запуска (генерация)

После `odpm --skip-start` при `pydevd_connect`:

- `config.json`: `"backend": "pydevd_connect"`;
- compose: `extra_hosts`, нет `DEBUGGER_PORT:DEBUGGER_PORT`;
- `.run/Odoo Debug Server.run.xml` с `PyRemoteDebugConfigurationType`.

---

## Чеклист manual verification (PyCharm Pro)

End-to-end с PyCharm Pro в репозитории **не зафиксирован автоматически**. Перед релизом этапа 2 рекомендуется:

- [ ] Run **Odoo Debug Server** → *Waiting for process connection...*
- [ ] `odpm` → контейнер подключается
- [ ] Breakpoint в addon срабатывает
- [ ] `ODPM_DEBUGGER_SUSPEND=1` — Odoo ждёт Resume

---

## На сервере и в CI

В сценариях **`server`** и **`ci`** отладчик **не используется**. Не включайте `developer` на production ради отладки.

---

## Другие IDE

| ID | Задача | Статус |
|----|--------|--------|
| TD-FEAT-08a | PyCharm Attach to DAP (`debugpy_listen`) | реализовано |
| TD-FEAT-08b | PyCharm Debug Server (`pydevd_connect`) + ручной `settrace` для прочих IDE | реализовано (документация выше) |
