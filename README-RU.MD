[![CI](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml)
[![CI Docker](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml)
[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/aayartsev/odoo_dev_project/blob/3.0/README.MD)

# Менеджер для разработки проектов на odoo (Odoo Developer Project Manager)

## Цель проекта
Основная цель проекта - создать инструмент для разработчика на платформе odoo, который будет удовлетворять следующим требованиям:
- не зависеть от операционной системы
- по возможности не зависеть от архитектуры процессора (Для примера запуск на MacOS на базе M1)
- для передачи всей информации о проекте, достаточно иметь в репозитории проекта `odpm.json`, и система на его базе сможет легко подготовить новое окружение в полностью автоматическом режиме
- иметь удобные инструменты, которые часто необходимы разработчику, например:
    - быстрое удаление БД
    - быстрое восстановление БД из архива
    - создание новой БД со своими настройками (страна, язык, демо-данные и прочее)
    - смена логина и пароля для администратора
    - ... и многое другое
    - механизмы для расширения функционала, на будущее

Если вы новичок, то рекомендуется использовать данный проект в связке с учебным демо [`https://github.com/aayartsev/odoo_demo_project`](https://github.com/aayartsev/odoo_demo_project).

## Подготовка
вам необходимо скачать и установить следующие программы:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) для пользователей Windows и MacOS
- [git](https://git-scm.com/)
- [python3](https://www.python.org/)
- [Visual Studio Code](https://code.visualstudio.com/)

## Установка

### pip (4.0+)

Нужен **Python 3.10 или новее**. На Linux с [PEP 668](https://peps.python.org/pep-0668/) (системный Python «защищён» от pip) устанавливайте odpm в virtualenv или через [pipx](https://pipx.pypa.io/), а не командой `pip install` в систему.

Из клона репозитория:

```bash
pip install /path/to/odoo_dev_project
# editable для разработки odpm:
pip install -e /path/to/odoo_dev_project
odpm --version
```

Консольная команда `odpm` использует шаблоны из установленного пакета `dev_project` (layout site-packages).

### Legacy copy

Скопируйте `odpm.py` и каталог `dev_project/` в рабочее пространство (или клонируйте репозиторий) и запускайте:

```bash
python3 /path/to/odoo_dev_project/odpm.py --version
```

Оба способа установки поддерживаются.

## Переводы host CLI (gettext)

Сообщения host CLI идут через GNU gettext. Каталог `main` — в `dev_project/i18n/<locale>/LC_MESSAGES/`. Локаль берётся из `LC_ALL`, `LC_MESSAGES` или `LANG` (например `ru_RU.UTF-8`).

**Обновление каталогов после правки строк `_('...')` в `dev_project/`:**

```bash
# 1) Извлечь msgid из исходников (опционально при ручном редактировании .po)
xgettext -o dev_project/i18n/main.pot -L Python -k_ dev_project/*.py dev_project/**/*.py

# 2) Слить в файл локали (пример: русский)
msgmerge -U dev_project/i18n/ru_RU/LC_MESSAGES/main.po dev_project/i18n/main.pot

# 3) Отредактировать dev_project/i18n/ru_RU/LC_MESSAGES/main.po (msgstr)

# 4) Скомпилировать .mo для wheel/deb
msgfmt -o dev_project/i18n/ru_RU/LC_MESSAGES/main.mo \
  dev_project/i18n/ru_RU/LC_MESSAGES/main.po

# Быстрый путь: таблица в scripts/sync_i18n_catalog.py + msgfmt
python3 scripts/sync_i18n_catalog.py

# Проверить, что каждый _('...') в dev_project/ есть в таблице ru_RU
python3 scripts/check_i18n_catalog.py
```

Скомпилированные `dev_project/i18n/**/LC_MESSAGES/*.mo` хранятся в git (исключение в `.gitignore`) и попадают в пакет через `package-data` в `pyproject.toml`. Поведение локали — в `tests/test_translations.py`.

## Тесты репозитория

Unit-тесты запускаются при каждом push и pull request в ветки `4.0-beta` и `main` через [GitHub Actions](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml) (Python 3.10 и 3.12). Badge в начале файла показывает статус последнего прогона на `4.0-beta` после того, как workflow хотя бы раз отработал на удалённой ветке.

Локально (та же команда, что в CI):

```bash
cd /path/to/odoo_dev_project
pip install -e .
python3 -m unittest discover -s tests -p 'test_*.py'
```

Ожидается **634** passed и **7** skipped (opt-in Docker integration tests). Повторный запуск в GitHub: **Actions → CI → Run workflow**.

### Docker CI

[`.github/workflows/ci-docker.yml`](.github/workflows/ci-docker.yml) параллельно с [unit CI](.github/workflows/ci.yml) на push/PR в `4.0-beta` и `main`.

#### Матрица CI (политика 4.2)

| Job | Workflow | Триггер | Gate на merge | Fixture / входы |
|-----|----------|---------|---------------|-----------------|
| **unit** | `ci.yml` | каждый push/PR | **обязателен** (рекомендуется) | `tests/` unittest discover; Python **3.10** и **3.12** |
| **compose-smoke** | `ci-docker.yml` | каждый push/PR | **обязателен** (рекомендуется) | [`tests/fixtures/minimal_odpm_project/`](tests/fixtures/minimal_odpm_project/) — stub platform/developing; `odpm --skip-start --no-git-update`, `docker compose config`. Только Python **3.12**. Кэш base-образа между прогонами. |
| **golden-path** | `ci-docker.yml` | nightly (`03:00` UTC), `workflow_dispatch` (+ флаг golden), или label PR **`run-docker`** | **opt-in** (не на каждый PR) | Secret `ODPM_GOLDEN_PATH_PROJECT` → реальный инициализированный проект (`tests.integration.test_golden_path`). Без secret job **пропускается** — не ложный pass. |

**Label PR `run-docker`:** добавьте label в GitHub, затем **перезапустите** workflow **CI Docker** (одного label недостаточно для нового прогона).

**Локально:**

```bash
# Compose smoke (как job compose-smoke в CI)
./scripts/run_compose_smoke_test.sh

# Full golden-path (нужен реальный проект на диске)
./scripts/run_golden_path_test.sh
```

#### CI secrets и branch protection

| Имя | Для чего | Примечание |
|-----|----------|------------|
| `ODPM_GOLDEN_PATH_PROJECT` | только job `golden-path` | Абсолютный путь к инициализированному odpm-проекту на runner (обычно **self-hosted**). Compose smoke использует minimal fixture из репозитория и **не** требует этот secret. |

Рекомендуется branch protection на `4.0-beta` / `main`: обязательные checks **CI** (unit) и **CI Docker** / **compose-smoke**. **golden-path** — nightly или по запросу, пока нет стабильного self-hosted runner; сделать golden-path обязательным только на `main` — разумный следующий шаг (4.3).

### Миграция импортов 4.0→4.1

**Начиная с 4.1.0, root-shim модули в `dev_project/` удалены.** Используйте канонические пути ниже; старые импорты завершатся `ModuleNotFoundError`.

| Удалённый импорт (shim 4.0) | Используйте вместо |
|---|---|
| `dev_project.prepare_registry` | `dev_project.prepare` |
| `dev_project.plan_compose_preview` | `dev_project.plan.compose_preview` |
| `dev_project.plan_runtime_preview` | `dev_project.plan.runtime_preview` |
| `dev_project.plan_compose_runtime` | `dev_project.plan.compose_runtime` |
| `dev_project.plan_diff` | `dev_project.plan.diff` |
| `dev_project.plan_format` | `dev_project.plan.format` |
| `dev_project.plan_cli` | `dev_project.plan.cli` |
| `dev_project.compose_service_builder` | `dev_project.compose.service_builder` |
| `dev_project.compose_runtime` | `dev_project.compose.runtime` |
| `dev_project.compose_command_render` | `dev_project.compose.command_render` |
| `dev_project.start_command` | `dev_project.compose.start_command` |
| `dev_project.host_context` | `dev_project.host.context` |
| `dev_project.host_runtime` | `dev_project.host.runtime` |
| `dev_project.host_user_env` | `dev_project.host.user_env` |
| `dev_project.host_cli` | `dev_project.host.cli` |
| `dev_project.host_cli.args` | `dev_project.host.cli.args` |
| `dev_project.host_cli.parse_args` | `dev_project.host.cli.parse_args` |
| `dev_project.host_cli.params` | `dev_project.host.cli.params` |
| `dev_project.inside_docker_app.cli_params` | `dev_project.host.cli.params` (host); флаги checker: `dev_project.inside_docker_app.params` |
| `dev_project.inside_docker_app.parse_args` | `dev_project.host.cli.parse_args` (только host) |
| `dev_project.project_env.compose` | `dev_project.compose.generator.ComposeGenerator` или `from dev_project.compose import ComposeGenerator` |

Имена CLI-флагов checker в контейнере: `dev_project.inside_docker_app.params` (host CLI: `dev_project.host.cli.params`).


## Как начать работать

Создаете папку где у вас будет располагаться новое окружение для нового проекта. В конца имени каталога я добавляю еще через дефис номер версии odoo. Например `odoo_demo_project-17`. Это связано с тем, что разница между версиями весьма существенна и я рассматриваю одни и те же модули для разных версий как разные проекты для разработки. Для каждой версии odoo необходимо свое окружение. Даже не смотря на то, что код одного и того же проекта может находится в одном репозитории. Для того, чтобы утилита начала создавать окружение, необходимо перейти в созданный ранее вами каталог, например `odoo_demo_project-17`, а затем его инициировать с помощью команды параметра `--init`. В качестве параметра команды `--init` можем указать ссылку на гит репозиторий (или локальный каталог). Так же добавив параметр `--branch` можно указать конкретную ветку, на которую хотим переключить репозиторий разрабатываемого проекта. Если параметр `--branch` не указан, то будет выбрана ветка по умолчанию:

Запускаем `VSCode` затем через меню Файл - Открыть (File - Open Folder) Каталог, открываем ранее созданный каталог `odoo_demo_project-17`.

Теперь запускаем терминал через меню Терминал - Создать Терминал (Terminal - New Terminal) и уже в нем вводите указанные ниже команды. Если кто-то, глядя на python скрипт захочет запустить его внутри виртуального окружения, то не надо этого делать. В данном случае он используется вместо системных скриптовых языков и вы только усложните себе жизнь. Виртуальное окружение для проекта будет установлено внутрь контейнера.

При самом первом запуске ранее описанной команды:
```bash
python3 /путь/к/клонированному/odoo_dev_project/odpm.py --init https://github.com/aayartsev/odoo_demo_project.git --branch 17.0-test_odpm_json
```
Если вы не хотите связываться с `git` репозиторием по какой-либо причине, то вы можете создать локальный проект для разработки, просто указав нужный каталог место е

```bash
python3 /путь/к/клонированному/odoo_dev_project/odpm.py --init file:///ваш/путь/к/каталогу/odoo_demo_project-17/имя_каталога_проекта_разработки
```

Утилита будет пытаться подготовить ваш компьютер:
1. Утилита будет задавать вопросы о том, какие параметры надо сохранить в файл `.env` (в том числе сценарий использования: `developer` или `server`)
1. Если вы разворачиваете проект с нуля, утилита попросит уточнить вас версию odoo и на основании этой информации сделает первоначальные настройки
1. Будет запущен процесс клонирования основного репозитория odoo. Это занимает весьма значительное время 40 минут и более, поэтому наберитесь терпения
1. Будет клонирован репозиторий разрабатываемого проекта или же подключен каталог локальной файловой системы, если был указан путь к файловой системе
1. Будет автоматически сгенерирован `Dockerfile` для указанного дистрибутива и версии python
1. Из шаблона `.odpm/dockerignore` будет сгенерирован `.dockerignore` в корне проекта (контекст `docker build`)
1. После этого запустится автоматическая сборка `Docker образа`, если он не был собран ранее
1. Будет автоматически сгенерирован файл `docker-compose.yml`
1. Для VSCode будет сгенерирован конфигурационный файлы для корректной работы отладчика
1. Автоматически запустится `docker-compose up`
1. Будут установлены все python зависимости в виртуальное окружение
1. Запустится odoo в обычном режиме

Остановить данный запущенный процесс можно сочетанием клавиш `Ctrl+C`.

После этого можно запустить odoo в режиме разработчика
```bash
python3 /путь/к/клонированному/odoo_dev_project/odpm.py -d test_db -i -u
```
Данная команда запустит odoo внутри Docker контейнера и создаст новую базу с именем `test_db` и установит туда модуль из указанного проекта

После этого вы можете открыть в браузере адрес `http://127.0.0.1:8069` и увидите окно входа в систему.

Для работы системы требуется 2 конфигурационных файла:
- `odpm.json` -  может находится в репозитории с проектом, содержит в себе необходимой информацию о том, как запустить данный проект
- `user_settings.json` - если файл не найден, он будет создан из значений по умолчанию. Содержит настройки и предпочтения конкретного разработчика

## Небольшое обобщение

Данное приложение формирует в указанном каталоге окружение для проекта. Сам же проект, это каталог, который указан в параметре `developing_project` файла `user_settings.json` или ключ параметра `--init`.

### Шаблон `.dockerignore`

Правила исключений для `docker build` редактируются в `.odpm/dockerignore` (шаблон копируется из odpm при инициализации проекта). При каждом запуске odpm пересоздаёт корневой `.dockerignore` из этого шаблона — файл в корне не редактируют вручную. Чтобы вернуть шаблон к значениям odpm, удалите `.odpm/dockerignore` и снова запустите odpm.

## Параметры .env:
Система попытается создать в домашнем каталоге пользователя вашей операционной системы каталог `.odpm` внутри которого поместит файл `.env`. Если вы запускаете приложение первый раз, то оно задаст вопрос по каждому ниже описанному пункту данного файла и предложит значения по умолчанию. Если вы не знаете что ответить просто жмите `Enter`. Если вы поместите файл`.env` в каталог с проектом то программа будет считать его приоритетным и попытается взять значения из файла внутри проекта.
- `BACKUP_DIR` - каталог в котором находятся архивы. Используется для того, чтобы с помощью параметров командной строки указать имя базы для восстановления и тогда система будет искать архив с указанным именем в этом каталоге, или при сохранении базы в архив, он появится в этом каталоге, может применяться для всех проектов
- `ODOO_PROJECTS_DIR` - создайте каталог, в котором будут создаваться клоны всех используемых репозиториев. Нужно только его создать и указать путь к этому каталогу, дальше система сама клонирует в него все репозитории и расположит их так, чтобы не возникало конфликтов
- `PATH_TO_SSH_KEY` - если, по каким либо причинам у вас не получается добавить в ssh агент свой ключ для репозитория, то можете указать путь к нему здесь. На данный момент будет использоваться один ключ для всех репозиториев
- `ODOO_PORT` - порт на котором по умолчанию будет запускаться odoo на адресе 127.0.0.1
- `POSTGRES_PORT` - порт на котором по умолчанию будет запускаться СУБД PostgreSQL на адресе 127.0.0.1
- `DEBUGGER_PORT` - порт на котором по умолчанию будет запускаться отладчик на адресе 127.0.0.1
- `GEVENT_PORT` - порт, на котором по умолчанию будет слушать Websocket Gevent System
- `ODPM_SCENARIO` - сценарий использования odpm: `developer` (по умолчанию), `server` или `ci`. Подробнее в разделе [Сценарии использования](#сценарии-использования-odpm_scenario).

Пример:
```conf
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=/home/user/.ssh/my_ssh_key
ODOO_PORT=8069
POSTGRES_PORT=5432
DEBUGGER_PORT=5678
GEVENT_PORT=8072
ODPM_SCENARIO=developer
```

## Неинтерактивный запуск (CI, скрипты)

Если stdin не подключён к терминалу (нет TTY), odpm **не задаёт вопросы** через `input()`. В сценарии **server**, если локально нет исходников platform (`odoo-bin`), odpm в интерактивном режиме предлагает скачать nightly zip; без TTY выполняется **fail-fast** — установите исходники заранее, запустите из интерактивного терминала или используйте `ODPM_SCENARIO=developer` для git-клонирования на этапе prepare.

**Файл `.env`** — должен уже существовать в каталоге проекта или в `~/.odpm/.env`. Альтернатива для первого запуска: задайте хотя бы одну переменную окружения из списка ниже — odpm создаст `~/.odpm/.env`, подставив остальные значения по умолчанию:

- `BACKUP_DIR`, `ODOO_PROJECTS_DIR`, `PATH_TO_SSH_KEY`
- `ODOO_PORT`, `POSTGRES_PORT`, `DEBUGGER_PORT`, `GEVENT_PORT`
- `ODPM_SCENARIO`

**Создание `odpm.json`** — при `--init` без готового `odpm.json` в developing project укажите `--odoo-version` или положите `odoo_version` в `odpm.json` репозитория (после клонирования developing project).

Пример для CI:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/acme/demo.git --skip-start
```

## Сценарии использования (`ODPM_SCENARIO`)

При первом запуске odpm предложит выбрать сценарий по номеру (`1` — developer, `2` — server, `3` — ci). Значение сохраняется в `.env` как `ODPM_SCENARIO`. Его можно изменить позже и пересоздать `docker-compose.yml`, снова запустив odpm.

Сценарий **не заменяет** `odpm.json` и `user_settings.json`. Он влияет на публикацию портов Docker, команду запуска Odoo (с `debugpy` или без) и режим venv (`fresh` / `baked`; см. таблицу сравнения).

### `developer` (по умолчанию)

Для **локальной разработки**: отладка в VS Code и режим разработчика Odoo.

| Область | Поведение |
|---------|-----------|
| **debugpy** | Включается **внутри контейнера** модулем `run_odoo` при `ODPM_SCENARIO=developer` (не в списке `command` в compose). Слушает `0.0.0.0:5678`; порт отладчика пробрасывается на хост. |
| **PostgreSQL / отладчик на хосте** | Проброс `ПОРТ_ХОСТА:ПОРТ_КОНТЕЙНЕРА` без привязки только к loopback. |
| **Odoo / Gevent** | Доступны на хосте на `ODOO_PORT` и `GEVENT_PORT`. |
| **`dev_mode` в `user_settings.json`** | Передаётся в Odoo как `--dev` в compose (отдельного CLI-флага odpm нет). Значения: `reload`, `qweb`, `werkzeug`, `xml`, `access`, `all` или комбинации через запятую. При `reload` или `all` в venv автоматически добавляется `inotify`. После смены `dev_mode` пересоздайте compose через `odpm --skip-start`. |

Типично: `ODPM_SCENARIO=developer`, подключение отладчика из VS Code, `http://127.0.0.1:8069`.

### `server`

Для **сервера** (staging/production, VPS): меньше открытых служебных портов, без отладчика в процессе Odoo.

| Область | Поведение |
|---------|-----------|
| **debugpy** | **Не устанавливается** и в команду запуска Odoo **не** добавляется. Для отладки переключитесь на `ODPM_SCENARIO=developer` и пересоздайте окружение. |
| **PostgreSQL на хосте** | Только `127.0.0.1:POSTGRES_PORT` (с других машин через этот проброс не подключиться). |
| **Порт отладчика в compose** | **Не публикуется** (debugpy в процессе Odoo не используется). |
| **Odoo / Gevent на хосте** | По-прежнему `ODOO_PORT` / `GEVENT_PORT` на всех интерфейсах хоста — для доступа из интернета используйте reverse proxy (nginx, traefik) и firewall. |
| **`dev_mode`** | **Игнорируется** в сценарии `server` (warning в лог). На production оставьте пустым в `user_settings.json`. |

### `ci` (CI / DevOps)

Для **сборки и запуска baked-образа** на runner: исходники и venv внутри Docker-образа, без bind-mount каталогов Odoo.

| Область | Поведение |
|---------|-----------|
| **Образ** | Project-specific CI-образ (`odpm --build-image`, только при `ODPM_SCENARIO=ci`) |
| **Volumes odoo** | Нет bind-mount исходников |
| **debugpy / debugger port** | Нет (debugpy не устанавливается в `ci`) |
| **Gevent 8072** | Да (как в dev/server) |
| **Entrypoint** | В compose exec form: `python3 -m dev_project.inside_docker_app.run_odoo`; конфиг проекта монтируется из `.odpm/runtime/config.json` (`venv_mode=baked`) |
| **VS Code** | Не настраивается |
| **`dev_mode`** | **Игнорируется** (как в `server`) |

Типично на runner: `ODPM_SCENARIO=ci`, `odpm --build-image`, затем `docker compose up`.

**Ручная проверка** (полный проект с реальными исходниками Odoo):

```bash
export ODPM_SCENARIO=ci
./scripts/verify_ci_scenario.sh
```

Скрипт запускает `python3 odpm.py --build-image`, `docker compose up -d` и ждёт HTTP 200 на `/web`.

**Opt-in integration-тесты docker** (нужен Docker на хосте; по умолчанию пропускаются в `unittest discover`):

```bash
# Compose smoke: minimal fixture + odpm --skip-start + docker compose config
./scripts/run_compose_smoke_test.sh

# Только сборка CI-образа (minimal context, без compose)
ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_ci_image_build -v

# Golden path: compose up + HTTP 200 на /web (полностью инициализированный проект)
export ODPM_GOLDEN_PATH_PROJECT=/path/to/your/odpm/project
# Запуск из корня репозитория odpm (пакет tests/ там), или через скрипт:
./scripts/run_golden_path_test.sh
# Эквивалент:
# cd /path/to/odoo_dev_project && ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_golden_path -v
```

Опционально: `ODPM_GOLDEN_PATH_TIMEOUT=600` (секунды, по умолчанию 300). Сначала остановите основной stack проекта (`docker compose down` в каталоге проекта): golden-path тест использует тот же каталог данных Postgres и ephemeral host-порты (Postgres не публикуется; HTTP Odoo — на свободный порт).

Нужен Docker на хосте. По умолчанию пропускается в `unittest discover` (быстрый CI).

### Сравнение

| | `developer` | `server` | `ci` |
|---|-------------|----------|------|
| Удалённая отладка (debugpy) | Да | Нет | Нет |
| Postgres на хосте | Все интерфейсы | Только `127.0.0.1` | Только `127.0.0.1` |
| Порт debugger в compose | Да | Нет | Нет |
| Bind-mount odoo | Да | Да | Нет |
| Python venv (`venv_mode`) | `fresh` — пересоздаётся при смене lock | `fresh` — как у developer | `baked` — собран в образе, без recreate |
| `--build-image` | Ошибка | Ошибка | Да |
| Odoo `--dev` (`dev_mode`) | Да | Нет (игнорируется) | Нет (игнорируется) |
| Где использовать | Локальный ПК | Сервер / VPS | CI runner |

### Смена сценария

1. Измените `ODPM_SCENARIO` в `~/.odpm/.env` или в `.env` проекта.
2. Запустите odpm из каталога проекта (например `python3 .../odpm.py --skip-start`), чтобы пересоздать `docker-compose.yml`.
3. Перезапустите контейнеры: `docker compose up -d` (или запустите odpm без `--skip-start`).

Сгенерированный `docker-compose.yml` использует exec form `command:` (YAML-список), `working_dir` и read-only mount `.odpm/runtime/config.json` в контейнер. Runtime-файл генерируется автоматически (JSON с `schema_version: 1`, тип `ContainerConfig`) и добавлен в `.gitignore` — не редактируйте compose вручную; пересоздавайте через `odpm --skip-start` после обновления odpm или смены сценария/флагов CLI. Конфиг передаётся через mount и `ODPM_CONFIG_PATH`. Entrypoint контейнера — `python3 -m dev_project.inside_docker_app.run_odoo`.

### Рекомендации для `server`

- Перед запуском odpm в CI или скриптах (неинтерактивно) убедитесь, что исходники platform есть в `odoo_src_dir`. При первом интерактивном запуске odpm может предложить скачать nightly zip; без TTY нужен уже заполненный каталог или сценарий `developer`.
- `dev_mode` в `user_settings.json` на `server` игнорируется; не переключайтесь на `developer` на публичном инстансе ради `--dev`.
- Задайте надёжные `db_manager_password`, `db_default_admin_*` и пароль PostgreSQL; не оставляйте значения по умолчанию из образа.
- Выносите HTTPS на reverse proxy; при публикации Odoo настройте `proxy_mode` и `dbfilter` в `odoo.conf`.
- Ограничьте входящий трафик firewall (SSH, HTTPS; закройте прямой доступ к `8069`/`8072` из интернета, если proxy на той же машине).
- Для администрирования БД с хоста достаточно привязки Postgres к `127.0.0.1`; не пробрасывайте `5432` на `0.0.0.0` вручную в compose.

## Параметры user_settings.json:

- `init_modules` - Строка. Параметр, в котором указываются модули через запятую, без пробелов, которые будут про-инициированы(установлены) при (пере)запуске системы.
- `update_modules` - Строка. Параметр, в котором указываются модули через запятую, без пробелов, которые будут обновлены при (пере)запуске системы
- `db_creation_data` - Объект. Параметры которые определяют создание новой базы
    - `db_lang` - Строка. Укажите язык системы по умолчанию про создании новой базы, например: `"en_US"` или `"ru_RU"`
    - `db_country_code` - Строка или `false` Укажите код страны по умолчанию про создании новой базы, например:`"ru"`
    - `create_demo` - Булево. Указывает на то, нужно ли создавать в системе демо данные при создании новой базы.
    - `db_default_admin_login` - Строка. Логин для учетной записи администратора
    - `db_default_admin_password` - Строка. Пароль для учетной записи администратора
- `update_git_repos` - Булево. Указывает на то, будут ли обновлены репозитории зависимостей и самой odoo при перезапуске системы
- `clean_git_repos` - Булево. Указывает на то, будут ли при перезапуске сбрасываться изменения в самой odoo и проектах зависимостей
- `check_system` - Булево. При `true` включает beginner-проверки через `SystemCheckPolicy` (`dev_project/system_check_policy.py`): `beginner_git` (`git --version` при setup pipeline) и prepare-шаг `docker.engine.check` (членство в группе Docker, `docker info`, base image). **Не** управляет освобождением портов — `developer_port_release` запускает prepare-шаг `docker.ports.release` только в сценарии **developer**, даже при `check_system: false`. **Не** отключает `compose.validate` (`compose_validate` всегда включён). `file_system_on_init` всегда создаёт каталоги backup/project при инициализации checker и в сценарии **developer** проверяет platform git (clone/update — позже в prepare-шаге `git.materialize`, не при init). Свободное место на диске проверяется только при clone исходников Odoo, не через этот флаг.
- `developing_project` - Строка. Ссылка на проект, который вы разрабатываете. Пример: `"git@github.com:aayartsev/odoo_demo_project.git"`
- `pre_commit_map_files` - Список. Список файлов для системы `pre-commit`, которые выносятся из проекта и пробрасываются туда через сопоставление файлов docker. Нужно для работы не на Linux системах
- `dev_mode` — строка или `false`. [Флаги Odoo `--dev`](https://www.odoo.com/documentation/16.0/developer/reference/cli.html?highlight=dev#cmdoption-odoo-bin-dev) через запятую (`reload`, `qweb`, `werkzeug`, `xml`, `access`, `all`). **Применяется только при `ODPM_SCENARIO=developer`**; в `server`/`ci` значение игнорируется с warning. При `reload` или `all` odpm добавляет `inotify` в Python requirements для autoreload. После изменений пересоздайте compose (`odpm --skip-start`).
- `db_manager_password` - пароль для менеджера баз данных
- `sql_queries` - Список. Содержит в себе список строк, каждая из которых является sql скриптом, которые будут выполняться при использовании параметра командной строки `--sql-execute`
- `use_oca_dependencies` - экспериментальное discovery зависимостей (один запуск odpm, по умолчанию `false`): читает `oca_dependencies.txt` из developing-проекта и каждой checkout git-зависимости, **а также** вложенный `odpm.json` в корне repo-зависимости (`dependencies`, `requirements_txt`). Транзитивные git URL попадают в resolved graph и в `.odpm/deps.lock.json` при `--update-lock`. Вложенные `odoo_version` / `python_version` сверяются с host-проектом (warning в developer, error в CI). Не подменяет host `odoo_git_link` и platform.
- `create_module_links` — опциональная experimental-функция: симлинки модулей в `odoo/addons` под `odoo_src_dir` для language server. Симлинки в корне odpm-проекта (`odoo`, `developing` и т.д.) обновляются при каждом запуске `odpm`. VS Code debugger `pathMappings` указывают абсолютные пути к реальным каталогам. По умолчанию `false`.

## Параметры odpm.json:
- `python_version` - Строка. Версия python, указывается в текстовом виде его номер, например `"3.10"` или `"3.7"`,
- `distro_name` - Строка. Имя дистрибутива, на базе которого будет создаваться образ для запуска odoo. Над данный момент пока поддерживается только `"debian"`
- `distro_version` - Строка. Версия дистрибутива указанного в ключе `distro_name`, указывается в текстовом виде его версия или кодовое имя, например `"11"` или `"bullseye"`,
- `postgres_version` - Строка. Версия PostgreSQL для Docker Compose (например `"15"`).
- `odoo_version` - Строка. Версия системы. Примеры: `"16.0"`, `"15.0"`, `"11.0"`
- `dependencies` - Список. Список ссылок на репозитории проектов, от которых зависит ваш проект
- `requirements_txt` - Список. Список python модулей, каждый элемент может оформляться так же как и строка в файле requirements.txt
- `odoo_git_link` - Строка. URL репозитория platform; опционально ветка/коммит через пробел (как в `--odoo-git-link`).
- `platform_name` - Строка. Имя Python-пакета форка (по умолчанию `"odoo"`).
- `odoo_build_date` - Строка. Дата nightly (`YYYYMMDD`) или `"latest"`. Checkout коммита на ветке platform. Перекрывается CLI `--odoo-build-date`.
- `odpm_version` - Строка. Версия формата файла odpm в проекте.

### Поддерживаемые Linux дистрибутивы и версии в связке с версиями python
На данный момент для версии версий odoo с 11 по 16 включительно протестировано и стабильно работает python 3.7 на базе debian 11(bullseye).
Так же протестировано и стабильно работает версии odoo с 16 по 17 для версия python 3.10 на базе дистрибутивов debian 11(bullseye) и debian 12(bullseye)
Начата экспериментальная поддержка дистрибутивов ubuntu, но она пока в начальном состоянии и все эксперименты на ваше усмотрение.
Поддерживаемые дистрибутивы и версии:

- Стабильно:
    - Debian 11 (Bullseye)
        - Python 3.7, 3.10
    - Debian 12 (Bullseye)
        - Python 3.10
    - Debian 13 (Bullseye)
        - Python 3.10, 3.12


## Параметры командной строки

Полный список: `python3 /путь/к/odpm.py --help`. Ниже параметры сгруппированы по назначению.

### Инициализация проекта

| Параметр | Описание |
|----------|----------|
| `--init ССЫЛКА` | Инициализация текущего каталога как проекта odpm. `ССЫЛКА` — URL git, `git@…` или `file:///путь/к/локальному/проекту`. |
| `--branch ИМЯ` | С `--init`: ветка **разрабатываемого** репозитория. |
| `--odoo-version ВЕР` | С `--init`: версия Odoo (например `17.0`), попадает в `odpm.json`. |
| `--odoo-git-link ССЫЛКА` | С `--init`: репозиторий platform вместо официального `odoo/odoo`. Можно указать ветку (и коммит), например `'git@host:org/odoo-17.git 17.0'`. |
| `--platform-name ИМЯ` | С `--init` / свой git: имя Python-пакета форка (по умолчанию `odoo`). Влияет на пути и команду `*-bin` в контейнере. |
| `--python-version ВЕР` | С `--init`: версия Python в образе (например `3.10`). |
| `--distro-name ИМЯ` | С `--init`: имя дистрибутива Linux (сейчас `debian`). |
| `--distro-version ВЕР` | С `--init`: версия дистрибутива (например `12`). |
| `--postgres-version ВЕР` | С `--init`: версия PostgreSQL в compose (например `15`). |
| `--requirements-txt ПАКЕТЫ` | Python-пакеты через запятую с версиями, например `requests==2.31.0`. Записывается в `odpm.json`. |

Пример:

```bash
python3 odpm.py --init git@github.com/org/my_addons.git --branch 17.0 \
  --odoo-version 17.0 --odoo-git-link 'git@github.com/org/odoo-17.git 17.0' \
  --platform-name odoo --python-version 3.10 --distro-version 12
```

### Окружение и образ

| Параметр | Описание |
|----------|----------|
| `--skip-start` | Пересоздать `Dockerfile`, `.dockerignore`, `docker-compose.yml` и связанные файлы **без** запуска контейнеров. При наличии `.odpm/deps.lock.json` выполняет checkout по lock. |
| `--update-lock` | Зафиксировать platform, developing (remote git) и **полный resolved** graph (OCA + nested `odpm.json`) в `.odpm/deps.lock.json`; выход без запуска контейнеров. |
| `--no-git-update` | Не выполнять git clone/fetch/checkout. Lock **не** читается и не обновляется. Нужны локальные каталоги repos. |
| `--plan` | **Устарел.** То же, что `odpm plan` (см. [План (dry-run)](#plan-dry-run) ниже). |
| `--version` | Показать версию odpm и выйти. |

<a id="plan-dry-run"></a>

### План (dry-run)

Показать, какие шаги prepare и runtime выполнились бы при обычном запуске, **без** clone/update git-репозиториев, записи сгенерированных файлов (runtime config, корневой `docker-compose.yml`) и `docker compose up`.

```bash
odpm plan --skip-start
odpm plan --plan-format json | jq .
odpm plan --plan-show-diff --skip-start
```

`--plan` — устаревший alias; все флаги проекта (`--skip-start`, `--no-git-update` и т.д.) работают так же после `odpm plan`.

| Параметр | Описание |
|----------|----------|
| `--plan-format {table,json}` | Формат вывода. По умолчанию `table` (в лог). `json` пишется в **stdout** для скриптов (`jq`, CI). |
| `--plan-strict` | Код выхода `1`, если любой **обязательный** шаг будет `run` или `update`; `0`, если меняются только noop, skip или необязательные шаги. |
| `--plan-show-diff` | После таблицы шагов — unified diff файлов, которые изменятся: `.odpm/runtime/config.json`, корневой `docker-compose.yml`, корневой `.dockerignore`. |
| `--plan-no-docker` | Не вызывать `docker compose ps` / `inspect`; для `compose.up` не предсказывается `--force-recreate` (будет предупреждение). |

У каждого шага — исход (`RUN`, `UPDATE`, `NOOP`, `SKIP`), обязательность, id (например `git.materialize`, `compose.service`) и краткая причина. Если stack уже запущен и здоров, `compose.up` планируется без `--force-recreate`; иначе предсказывается recreate (кроме `--plan-no-docker` или `--skip-start`).

**Ограничения:** конфигурация всё равно читается из каталога проекта. В режиме plan шаблоны в `.odpm/` не обновляются (обычный запуск `odpm` по-прежнему их синхронизирует). Без `--plan-no-docker` odpm может проверить локальный compose stack для предсказания `compose.up`. С `--skip-start` шаг `compose.up` в план не попадает.

### Запуск Odoo: база и модули

| Параметр | Описание |
|----------|----------|
| `-d ИМЯ_БД` | Имя базы. Если базы нет — создаётся по `db_creation_data` из `user_settings.json`. |
| `-i` | Установить модули из `init_modules` (`user_settings.json`). |
| `-u` | Обновить модули из `update_modules` (`user_settings.json`). |
| `-t`, `--test` | Тесты модулей из `init_modules` / `update_modules`. Нужны `-d` и обычно `-i` или `-u`. На пустой БД тесты всех модулей могут идти долго. |
| `--screencasts` | С `-t` / `--test`: сохранять screencast при ошибках туров в `data/odoo/tmp/odoo_tests`. |
| `--odoo-bin АРГУМЕНТЫ…` | Аргументы для `odoo-bin` (всё после `--odoo-bin`). Пример: `--odoo-bin --stop-after-init`. |

Типичный запуск для разработки:

```bash
python3 odpm.py -d test_db -i -u
```

Установка модулей без долгого сервера (CI / первичная настройка):

```bash
python3 odpm.py -d test_db -i --odoo-bin --stop-after-init
```

### Platform git: дата nightly-сборки

| Параметр | Описание |
|----------|----------|
| `--odoo-build-date ДАТА` | Дата nightly: `YYYYMMDD` или `YYYY-MM-DD`. Последний коммит на ветке platform до конца этого дня, checkout. Перекрывает `odoo_build_date` в `odpm.json`. Игнорируется, если в `odoo_git_link` задан хеш коммита. |

Пример:

```bash
python3 odpm.py --skip-start --odoo-build-date 20250529
```

### Git dependency lock (`.odpm/deps.lock.json`)

Файл lock коммитится в репозиторий проекта (как `package-lock.json`).

| Команда | Поведение |
|---------|-----------|
| `python3 odpm.py --update-lock --skip-start` | Обновить lock (полный graph: OCA + nested `odpm.json`) и выйти без compose up |
| `python3 odpm.py --skip-start` | Prepare + checkout **по lock**, если файл есть |
| `python3 odpm.py --no-git-update --skip-start` | Offline regenerate; lock игнорируется |

После изменения `dependencies`, `oca_dependencies.txt` или nested `odpm.json` в зависимостях — `--update-lock` и commit lock.

Schema v1: `platform`, optional `developing` (только remote git), `dependencies` (полный resolved graph: seeds, OCA transitive, nested `odpm.json`). Поля entry: `url`, `commit`, optional `branch`, optional `kind` (`git` / `file` для `file://` platform).

Для `file://` platform `commit` — fingerprint содержимого (не git SHA). Стабилен при наличии `odoo/release.py` и `odoo-bin`; иначе может отличаться на разных машинах или после смены метаданных каталога — для CI и team sync надёжнее git remote.

Приоритет: `--no-git-update` > `--update-lock` > lock (pin SHA, без `odoo_build_date` для platform) > branch tip / build date.

### Резервное копирование и обслуживание БД

| Параметр | Описание |
|----------|----------|
| `--get-dbs-list` | Список баз данных. |
| `--db-backup [АРХИВ]` | Бэкап БД из `-d` в `BACKUP_DIR` (`.env`). Имя архива опционально. |
| `--db-restore АРХИВ` | Восстановить архив из `BACKUP_DIR` в БД из `-d`. |
| `--db-drop` | Удалить БД из `-d`. С `-d`, `-i`, `-u` и тем же именем: удалить, создать заново, установить модули. |

### Переводы и администратор

| Параметр | Описание |
|----------|----------|
| `--translate ЯЗЫК` | Обновить переводы (`ru_RU` и т.д.) для `-d` и модулей из `init_modules` / `update_modules`. С `-d`, `-i` или `-u`. |
| `--export-po-files ЯЗЫК` | Экспорт `pot` / `po` для модулей из `update_modules`. Нужен `-d`. |
| `--set-admin-pass` | Логин/пароль администратора (uid=2) из `db_default_admin_login` / `db_default_admin_password`. Нужен `-d`. |

### Инструменты разработки

| Параметр | Описание |
|----------|----------|
| `--start-precommit` | Запуск `pre-commit` в разрабатываемом проекте внутри контейнера. |
| `--sql-execute` | Выполнить SQL из `sql_queries` в `user_settings.json`. Нужен `-d`. |

### Подкоманда scaffold

Создание модуля в разрабатываемом проекте (запуск **без** других флагов odpm):

```bash
python3 odpm.py scaffold my_module_name
python3 odpm.py scaffold my_module_name -t /путь/к/шаблонам
```

| Параметр | Описание |
|----------|----------|
| `scaffold МОДУЛЬ` | Подкоманда: генерация модуля из шаблонов ([jinja2](https://jinja.palletsprojects.com/en/stable/)). |
| `-t`, `--scaffold_template_name КАТАЛОГ` | Каталог своих шаблонов. |
