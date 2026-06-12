# Переменные файла `.env`

Файл **`.env`** задаёт параметры **этого** каталога odpm-окружения: порты, сценарий, пути к резервным копиям и клонам git. Если он лежит **в каталоге проекта**, он **полностью заменяет** `~/.odpm/.env` — значения из двух файлов не смешиваются ([иерархия](config-hierarchy.md)).

При **первом интерактивном** запуске odpm задаёт вопросы мастера настройки и записывает ответы в `.env` (глобальный или проектный). На незнакомые пункты можно нажать Enter.

## Переменные

| Переменная | Назначение | Значение по умолчанию |
|------------|------------|------------------------|
| `BACKUP_DIR` | Каталог архивов баз (`--db-backup`, `--db-restore`) | `~/odoo_backups` |
| `ODOO_PROJECTS_DIR` | Куда клонировать platform и git-зависимости | `~/odoo_projects` |
| `ODOO_PORT` | HTTP-порт Odoo на компьютере | `8069` |
| `POSTGRES_PORT` | Порт PostgreSQL на компьютере (в сценарии `server` — только localhost) | `5432` |
| `DEBUGGER_PORT` | Порт отладчика (сценарий `developer`) | `5678` |
| `ODPM_DEBUGGER_BACKEND` | Режим отладки: `debugpy_listen` (контейнер слушает, IDE подключается) | `debugpy_listen` |
| `ODPM_IDE` | Какие настройки IDE генерировать: `vscode`, `pycharm`, `both`, `none` | `vscode` |
| `ODPM_DEBUGGER_CONNECT_HOST` | Хост IDE для `pydevd_connect` (этап 2) | `host.docker.internal` |
| `ODPM_DEBUGGER_SUSPEND` | `1` — ждать IDE перед стартом Odoo (этап 2) | `0` |
| `GEVENT_PORT` | Порт веб-сокетов gevent | `8072` |
| `ODPM_SCENARIO` | `developer`, `server` или `ci` | `developer` |
| `ODPM_LOCALE` | Язык сообщений odpm, напр. `ru_RU` | по системе | см. [locale.md](locale.md) |
| `PATH_TO_SSH_KEY` | Путь к ключу SSH для git (редко нужен) | пусто |

## Пример

```ini
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=
ODOO_PORT=8069
POSTGRES_PORT=5432
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=debugpy_listen
ODPM_IDE=vscode
GEVENT_PORT=8072
ODPM_SCENARIO=developer
ODPM_LOCALE=ru_RU
```

## SSH и git

Мастер настройки **не спрашивает** путь к SSH-ключу. Обычно достаточно настройки OpenSSH (`~/.ssh/config`, ssh-agent).

Переменная **`PATH_TO_SSH_KEY`** нужна, если git не может использовать стандартный SSH (типично на изолированной машине сборки):

```ini
PATH_TO_SSH_KEY=/home/user/.ssh/id_ed25519
```

Один ключ применяется ко всем указанным удалённым репозиториям.
