# Поля файла user_settings.json

Файл описывает **как работать** с уже заданным стеком (`odpm.json`): какой проект разрабатывать, какие модули ставить, как создавать базу. Если файла нет, odpm создаёт его из шаблона.

| Поле | Назначение |
|------|------------|
| `developing_project` | Ссылка на разрабатываемый репозиторий или каталог ([форматы ссылок](git-links.md)); поддерживает `${VAR}` — см. ниже |
| `init_modules` | Модули для установки при `-i` (через запятую, без пробелов) |
| `update_modules` | Модули для обновления при `-u` |
| `db_creation_data` | Параметры **новой** базы при первом `-d` |
| `db_creation_data.db_lang` | Язык базы, напр. `ru_RU` (не язык сообщений odpm) |
| `db_creation_data.db_country_code` | Код страны или `false` |
| `db_creation_data.create_demo` | Создавать ли демо-данные (по умолчанию `false` в новом `user_settings.json`) |
| `db_creation_data.db_default_admin_login` | Логин администратора |
| `db_creation_data.db_default_admin_password` | Пароль администратора |
| `update_git_repos` | Обновлять ли git при перезапуске |
| `clean_git_repos` | Сбрасывать ли локальные изменения в platform и зависимостях |
| `check_system` | Проверки Docker и git для новичков (по умолчанию `true`) |
| `dev_mode` | Режим разработки Odoo; только сценарий `developer` |
| `db_manager_password` | Пароль менеджера баз Odoo |
| `sql_queries` | Список SQL для `--sql-execute` |
| `pre_commit_map_files` | Файлы для pre-commit при работе не на Linux |
| `use_oca_dependencies` | Расширенный разбор OCA и вложенных `odpm.json` (по умолчанию `false`) |
| `create_module_links` | Символические ссылки для редактора (по умолчанию `false`) |

## Подстановка `${VAR}` в `developing_project`

Поле **`developing_project`** — единственное в `user_settings.json`, где odpm раскрывает `${ИМЯ}` / `${ИМЯ:-default}` при чтении файла. Источник значений: `export` / CI → project `.env` → default в строке.

```json
{
  "developing_project": "file://${DEVELOPING_PROJECT_DIR}"
}
```

```ini
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
```

Остальные поля `user_settings.json` подстановку **не** получают.

## Режим разработки Odoo (`dev_mode`)

Строка с флагами Odoo: `reload`, `qweb`, `werkzeug`, `xml`, `access`, `all` (см. документацию Odoo). В сценариях `server` и `ci` **игнорируется**. После изменения — `odpm --skip-start`.

## Проверка системы (`check_system`)

При `true` выполняются базовые проверки git и Docker. Не отключает валидацию compose. Освобождение занятых портов в режиме разработчика — отдельная логика.

## Символические ссылки (`create_module_links`)

Упрощают навигацию и отладку в VS Code — [отдельная статья](../operations/vscode-debug.md).
