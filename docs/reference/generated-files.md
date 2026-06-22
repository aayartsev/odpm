# Сгенерированные файлы

Часть файлов в каталоге проекта **создаёт и обновляет odpm**. Их не следует править вручную: при следующем запуске изменения будут потеряны или возникнет рассогласование с описанием в `odpm.json`.

| Файл | Как обновить |
|------|----------------|
| `docker-compose.yml` | `odpm` или `odpm --skip-start` |
| корневой `.dockerignore` | из шаблона `.odpm/dockerignore`; сброс шаблона — удалить `.odpm/dockerignore` и снова запустить odpm |
| `.odpm/runtime/config.json` | автоматически; в gitignore проекта |
| `.odpm/database/last_run.json` | при adoption и после успешной проверки checker; mount в контейнер; см. [database-state.md](database-state.md) |
| `.odpm/runtime/debug-profile.json` | автоматически в сценарии `developer` (`include_debugpy`); в gitignore |
| `.odpm/secrets.example.json` | шаблон при init; в git |
| `.odpm/secrets.json` | вручную или `--secrets-file`; в `.odpm/.gitignore` |
| `.odpm/runtime/secrets.json` | шаг `secrets.materialize`; mount в контейнер; в gitignore; см. [секреты](../operations/secrets.md) |
| `.vscode/launch.json`, `.vscode/settings.json` | `odpm --skip-start` при `ODPM_IDE=vscode` или `both` и `ODPM_DEBUGGER_BACKEND=debugpy_listen`; `settings.json` включает `python.analysis.extraPaths` для platform, developing и зависимостей |
| `.run/Odoo Remote Attach.run.xml` | `odpm --skip-start` при `ODPM_IDE=pycharm` или `both` и **`debugpy_listen`** (PyCharm Attach to DAP) |
| `.run/Odoo Debug Server.run.xml` | `odpm --skip-start` при `ODPM_IDE=pycharm` или `both` и **`pydevd_connect`** (PyCharm Debug Server, Pro) |
| `Dockerfile` (корень проекта) | из шаблона `.odpm/{distro}_{ver}_dockerfile_{profile}`; профиль зависит от `ODPM_SCENARIO` |
| `.odpm/base_image_identity.json` | после успешного `docker build` base image; в `.odpm/.gitignore`; поля `base_image_profile`, `dockerfile_sha256` — см. ADR-007 |

При смене `ODPM_DEBUGGER_BACKEND` odpm удаляет неактуальный odpm-файл из пары выше (пользовательские `.run/*.run.xml` не трогает). См. [отладка в IDE](../operations/vscode-debug.md).

## Исключение: конфигурация Odoo

Файл **`odoo.conf`** (или `{platform_name}.conf`) **редактируется пользователем**, но odpm при подготовке пересчитывает пути к дополнениям и каталог данных под контейнер. См. [odoo.conf](odoo-conf.md).

## Зачем так устроено

Ручное редактирование `docker-compose.yml` ломает **единый контракт** между хостом и контейнером (порты, точка входа, передача конфигурации). odpm генерирует compose из сценария и параметров командной строки, чтобы разработчик, администратор и сборка оставались на одном описании проекта.

После обновления версии odpm или смены `ODPM_SCENARIO` выполните **`odpm --skip-start`** и перезапустите контейнеры.
