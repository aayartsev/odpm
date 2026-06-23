#!/usr/bin/env python3
"""Regenerate dev_project i18n catalogs from the embedded message table."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.plan_l10n_ru_batch import PLAN_L10N_RU  # noqa: E402

I18N_DIR = ROOT / "dev_project" / "i18n"
RU_PO = I18N_DIR / "ru_RU" / "LC_MESSAGES" / "main.po"
RU_MO = I18N_DIR / "ru_RU" / "LC_MESSAGES" / "main.mo"
EN_US_PO = I18N_DIR / "en_US" / "LC_MESSAGES" / "main.po"

# msgid (English) -> msgstr (Russian). Keep sorted by msgid for review.
RU_MESSAGES: dict[str, str] = {
    "--build-image is only allowed when ODPM_SCENARIO=ci in .env": (
        "--build-image доступен только при ODPM_SCENARIO=ci в .env"
    ),
    "--sync-manifest-locks is only supported in developer scenario; "
    "manifest locks.git unchanged": (
        "--sync-manifest-locks поддерживается только в developer-сценарии; "
        "manifest locks.git не изменён"
    ),
    "--sync-manifest-locks requires --update-lock": (
        "--sync-manifest-locks требует --update-lock"
    ),
    "--update-lock cannot be used together with --no-git-update": (
        "Нельзя использовать --update-lock вместе с --no-git-update"
    ),
    ' "config.json" is deprecated. Please read documentation': (
        ' Файл с параметрами "config.json" является устаревшим. '
        "Пожалуйста обратитесь к документации "
    ),
    "Action   Required  ID                    Reason": (
        "Действие  Обязат.   ID                    Причина"
    ),
    "Applying git dependency lock from manifest locks.git in odpm.json": (
        "Применение git lock из manifest locks.git в odpm.json"
    ),
    "Applying git dependency lock from {PATH}": (
        "Применение git lock из {PATH}"
    ),
    "Loaded git dependency lock from manifest locks.git": (
        "Загружен git lock зависимостей из manifest locks.git"
    ),
    "Local plugin module not found: {PATH}": (
        "Локальный модуль плагина не найден: {PATH}"
    ),
    "Local plugin path escapes .odpm/plugins: {NAME!r}": (
        "Путь локального плагина выходит за пределы .odpm/plugins: {NAME!r}"
    ),
    "Cannot connect to the Docker daemon. Is the docker daemon running?": (
        "Не удалось выполнить подключение к службе Docker. "
        "Проверьте запущена ли она."
    ),
    "Cannot create dir, {dir_path}, please check it": (
        "Не удалось создать каталог, {dir_path}, пожалуйста проверьте его."
    ),
    "Cannot get docker-compose info, did you install it?": (
        "Не удалось получить информацию о Docker Compose. "
        "Проверьте установлен ли он."
    ),
    "Cannot list Docker containers: {DETAILS}": (
        "Не удалось получить список контейнеров Docker: {DETAILS}"
    ),
    "Cannot load local plugin module: {PATH}": (
        "Не удалось загрузить локальный модуль плагина: {PATH}"
    ),
    "Blocking database configuration drift detected; resolve before starting containers.": (
        "Обнаружен блокирующий дрейф конфигурации БД; устраните его перед запуском контейнеров."
    ),
    "Blocking database configuration drift remains after resolution: {KINDS}": (
        "После разрешения дрейфа остаётся блокирующий дрейф конфигурации БД: {KINDS}"
    ),
    "Canonical git pins: odpm.json locks.git; run --update-lock to "
    "refresh .odpm/deps.lock.json.": (
        "Канонические git-пины: locks.git в odpm.json; выполните --update-lock, "
        "чтобы обновить .odpm/deps.lock.json."
    ),
    "Bootstrapping PostgreSQL application role {ROLE} in single-user mode.": (
        "Создание роли приложения PostgreSQL {ROLE} в single-user режиме."
    ),
    "Accepted database drift: {KIND}": (
        "Принят дрейф конфигурации БД: {KIND}"
    ),
    "Application role {ROLE} present: {VALUE}": (
        "Роль приложения {ROLE} присутствует: {VALUE}"
    ),
    "Adopting current database configuration as baseline (no last_run snapshot yet).": (
        "Принимаем текущую конфигурацию БД как baseline (снимок last_run ещё не создан)."
    ),
    "Check database configuration drift against last_run snapshot": (
        "Проверить дрейф конфигурации БД относительно снимка last_run"
    ),
    "Compose service: {SERVICE}": (
        "Сервис compose: {SERVICE}"
    ),
    "Configuration drift:": (
        "Дрейф конфигурации:"
    ),
    "Created {ENV_FILE} from environment variables and defaults (non-interactive mode).": (
        "Создан файл {ENV_FILE} из переменных окружения и значений по умолчанию "
        "(неинтерактивный режим)."
    ),
    "Created PostgreSQL application role {ROLE}.": (
        "Создана роль приложения PostgreSQL {ROLE}."
    ),
    "Data path: {PATH}": (
        "Каталог данных: {PATH}"
    ),
    "Database status": (
        "Состояние базы данных"
    ),
    "Database configuration drift requires confirmation in non-interactive mode. "
    "Drift kinds: {KINDS}. Use --accept-database-drift=KIND for each accepted drift.": (
        "Дрейф конфигурации БД требует подтверждения в неинтерактивном режиме. "
        "Типы дрейфа: {KINDS}. Используйте --accept-database-drift=KIND для каждого принятого дрейфа."
    ),
    "Database drift resolution aborted.": (
        "Разрешение дрейфа конфигурации БД отменено."
    ),
    "Did you install git?": "Вы установили git?",
    "extensions.local must be a list of module names": (
        "extensions.local должен быть списком имён модулей"
    ),
    "Error checking PostgreSQL port: {DETAIL}": (
        "Ошибка при проверке порта PostgreSQL: {DETAIL}"
    ),
    "No database last_run snapshot yet; baseline will be adopted automatically on startup.": (
        "Снимок last_run для БД ещё не создан; baseline будет принят автоматически при запуске."
    ),
    "No manifest changes to apply.": (
        "Нет изменений манифеста для применения."
    ),
    "No PostgreSQL admin role is available for service {SERVICE}.": (
        "Нет доступной административной роли PostgreSQL для сервиса {SERVICE}."
    ),
    "PostgreSQL admin role did not become available within {SECONDS}s after bootstrap.": (
        "Административная роль PostgreSQL не стала доступна за {SECONDS} с после bootstrap."
    ),
    "ODPM scenario changed: {PREVIOUS} -> {CURRENT}.\n"
    "Choose: (a) abort  (c) continue\n": (
        "Сценарий ODPM изменился: {PREVIOUS} -> {CURRENT}.\n"
        "Выберите: (a) отмена  (c) продолжить\n"
    ),
    "ODPM scenario changed: {PREVIOUS} -> {CURRENT}.": (
        "Сценарий ODPM изменился: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL compose service changed: {PREVIOUS} -> {CURRENT}.": (
        "Имя сервиса PostgreSQL в compose изменилось: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL application role {CURRENT} is missing in the running cluster.": (
        "Роль приложения PostgreSQL {CURRENT} отсутствует в работающем кластере."
    ),
    "PostgreSQL application role {ROLE} is missing in the running cluster.\n"
    "Choose: (a) abort  (b) create role now\n": (
        "Роль приложения PostgreSQL {ROLE} отсутствует в работающем кластере.\n"
        "Выберите: (a) отмена  (b) создать роль сейчас\n"
    ),
    "PostgreSQL application role {ROLE} is ready.": (
        "Роль приложения PostgreSQL {ROLE} готова."
    ),
    "PostgreSQL authentication failed for role {USER}": (
        "Ошибка аутентификации PostgreSQL для роли {USER}"
    ),
    "PostgreSQL connection failed: {DETAIL}": (
        "Не удалось подключиться к PostgreSQL: {DETAIL}"
    ),
    "PostgreSQL container running: {VALUE}": (
        "Контейнер PostgreSQL запущен: {VALUE}"
    ),
    "PostgreSQL container {SERVICE} is not running; start it before ensuring the role.": (
        "Контейнер PostgreSQL {SERVICE} не запущен; запустите его перед созданием роли."
    ),
    "PostgreSQL credentials check failed after {ATTEMPTS} attempts": (
        "Проверка учётных данных PostgreSQL не удалась после {ATTEMPTS} попыток"
    ),
    "PostgreSQL credentials check timed out after {SECONDS}s for database {DBNAME}": (
        "Истекло время проверки учётных данных PostgreSQL ({SECONDS} с) для базы {DBNAME}"
    ),
    "PostgreSQL in {SERVICE} is not ready yet; wait for startup before ensuring the role.": (
        "PostgreSQL в {SERVICE} ещё не готов; дождитесь запуска перед созданием роли."
    ),
    "PostgreSQL data directory changed: {PREVIOUS} -> {CURRENT}.": (
        "Каталог данных PostgreSQL изменился: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL data directory initialization state changed: {PREVIOUS} -> {CURRENT}.": (
        "Состояние инициализации каталога данных PostgreSQL изменилось: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL data directory initialization state changed: {PREVIOUS} -> {CURRENT}.\n"
    "Choose: (a) abort  (c) continue\n": (
        "Состояние инициализации каталога данных PostgreSQL изменилось: {PREVIOUS} -> {CURRENT}.\n"
        "Выберите: (a) отмена  (c) продолжить\n"
    ),
    "PostgreSQL data directory changed:\n"
    "  previous: {PREVIOUS}\n"
    "  current: {CURRENT}\n"
    "Choose: (a) abort  (b) accept new data path  (c) show wipe instructions\n": (
        "Каталог данных PostgreSQL изменился:\n"
        "  было: {PREVIOUS}\n"
        "  стало: {CURRENT}\n"
        "Выберите: (a) отмена  (b) принять новый каталог  (c) инструкция по очистке\n"
    ),
    "PostgreSQL host port changed: {PREVIOUS} -> {CURRENT}.": (
        "Порт PostgreSQL на host изменился: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL image version changed: {PREVIOUS} -> {CURRENT}.": (
        "Версия образа PostgreSQL изменилась: {PREVIOUS} -> {CURRENT}."
    ),
    "PostgreSQL image version changed:\n"
    "  previous: {PREVIOUS}\n"
    "  current: {CURRENT}\n"
    "Choose: (a) abort  (b) accept and continue  (c) show wipe instructions\n": (
        "Версия образа PostgreSQL изменилась:\n"
        "  было: {PREVIOUS}\n"
        "  стало: {CURRENT}\n"
        "Выберите: (a) отмена  (b) принять и продолжить  (c) инструкция по очистке\n"
    ),
    "PostgreSQL is still starting up": (
        "PostgreSQL ещё запускается"
    ),
    "PostgreSQL ready: {VALUE}": (
        "PostgreSQL готов: {VALUE}"
    ),
    "PostgreSQL role {USER} does not exist": (
        "Роль PostgreSQL {USER} не существует"
    ),
    "PostgreSQL service {SERVICE} did not become ready within {SECONDS}s during baseline adoption.": (
        "Сервис PostgreSQL {SERVICE} не стал готов за {SECONDS} с при принятии baseline."
    ),
    "PostgreSQL service {SERVICE} did not become ready within {SECONDS}s after single-user bootstrap.": (
        "Сервис PostgreSQL {SERVICE} не стал готов за {SECONDS} с после single-user bootstrap."
    ),
    "PostgreSQL startup timeout exceeded": (
        "Превышено время ожидания запуска PostgreSQL"
    ),
    "database configuration drift detected: {KINDS}": (
        "Обнаружен дрейф конфигурации БД: {KINDS}"
    ),
    "database configuration matches last_run snapshot": (
        "Конфигурация БД совпадает со снимком last_run"
    ),
    'database subcommand required: use "odpm database status" or '
    '"odpm database ensure-role".': (
        'Укажите подкоманду database: "odpm database status" или '
        '"odpm database ensure-role".'
    ),
    "first database run (no last_run snapshot yet)": (
        "Первый запуск БД (снимок last_run ещё не создан)"
    ),
    "odoo.conf db_host ({CURRENT}) does not match postgres service name ({PREVIOUS}).": (
        "В odoo.conf db_host ({CURRENT}) не совпадает с именем сервиса postgres ({PREVIOUS})."
    ),
    "odoo.conf db_host: {HOST}": (
        "odoo.conf db_host: {HOST}"
    ),
    "odoo.conf db_host out of sync with postgres service ({EXPECTED})": (
        "В odoo.conf db_host не синхронизирован с сервисом postgres ({EXPECTED})"
    ),
    "Directory {START_DIR_PATH} is not a valid odpm project directory. "
    "Please run \"cd {PROJECT_PATH}\" to navigate to the correct location.": (
        "Каталог {START_DIR_PATH} не является odpm катлогом, пожалуйста выполните "
        "команду cd {PROJECT_PATH} для перехода в нужный вам каталог"
    ),
    "Environment variable {VAR} is not set (required for manifest field {FIELD})": (
        "Переменная окружения {VAR} не задана (нужна для поля manifest {FIELD})"
    ),
    "Do not change this file, its content is generating automatically": (
        "Не изменяйте данный файл, его содержимое генерируется автоматически"
    ),
    "Do not change this param, it is generating automatically": (
        "Не изменяйте данный параметр, его значение генерируется автоматически"
    ),
    'Do not change, it will get from "db_manager_password" param from config.json file': (
        'Не изменяйте данный параметр, его значение будет взято из параметра '
        '"db_manager_password" файла конфигурации config.json'
    ),
    "Do you want to clone odoo? y/n\n": "Вы хотите клонировать odoo? y/n\n",
    "docker build failed with exit code {EXIT_CODE}": (
        "docker build завершился с кодом {EXIT_CODE}"
    ),
    "docker compose up failed with exit code {EXIT_CODE}": (
        "docker compose up завершился с кодом {EXIT_CODE}"
    ),
    "Failed to read nested {CONFIG_FILE_NAME} at {MANIFEST_PATH}: {ERROR}": (
        "Не удалось прочитать вложенный {CONFIG_FILE_NAME} ({MANIFEST_PATH}): {ERROR}"
    ),
    "Ensured PostgreSQL application role {ROLE} during baseline adoption.": (
        "Роль приложения PostgreSQL {ROLE} создана при принятии baseline."
    ),
    "Failed to start PostgreSQL service {SERVICE} for baseline adoption.": (
        "Не удалось запустить сервис PostgreSQL {SERVICE} для принятия baseline."
    ),
    "Failed to bootstrap PostgreSQL application role {ROLE} in single-user mode.": (
        "Не удалось создать роль приложения PostgreSQL {ROLE} в single-user режиме."
    ),
    "Failed to ensure PostgreSQL role {ROLE}.": (
        "Не удалось создать или обновить роль PostgreSQL {ROLE}."
    ),
    "File {SOURCE_FILE} with deprecated content was renamed to {DEPRECATED_FILE_NAME}": (
        "Файл {SOURCE_FILE} с устаревшим содержимым был переименован в "
        "{DEPRECATED_FILE_NAME}"
    ),
    "Git dependency {DEPENDENCY_URL} is not available locally; "
    "transitive entries from oca_dependencies.txt and nested odpm.json will be skipped": (
        "Git-зависимость {DEPENDENCY_URL} недоступна локально; "
        "транзитивные записи из oca_dependencies.txt и вложенного odpm.json "
        "будут пропущены"
    ),
    "Git lock source: .odpm/deps.lock.json; run --update-lock after "
    "changing dependencies.": (
        "Источник git lock: .odpm/deps.lock.json; после смены зависимостей "
        "выполните --update-lock."
    ),
    "Git lock source: manifest locks.git in odpm.json (canonical); "
    "edit SHA in locks.git and run --update-lock to sync "
    ".odpm/deps.lock.json.": (
        "Источник git lock: locks.git в odpm.json (канон); правьте SHA в locks.git "
        "и выполните --update-lock для синхронизации .odpm/deps.lock.json."
    ),
    "Host port: {PORT}": (
        "Порт на host: {PORT}"
    ),
    "Invalid choice. Please enter one of: {CHOICES}": (
        "Неверный выбор. Введите один из вариантов: {CHOICES}"
    ),
    "Invalid manifest hook {PHASE}: empty command": (
        "Недопустимый manifest hook {PHASE}: пустая команда"
    ),
    "Invalid manifest hook {PHASE}: empty plugin id": (
        "Недопустимый manifest hook {PHASE}: пустой id плагина"
    ),
    "Invalid manifest hook {PHASE}: expected command argv or plugin id": (
        "Недопустимый manifest hook {PHASE}: ожидается argv команды или id плагина"
    ),
    "manifest services.{NAME} is reserved; use service_patches.{NAME} to patch built-in services": (
        "manifest services.{NAME} зарезервировано; для patch встроенных сервисов используйте service_patches.{NAME}"
    ),
    "{SOURCE} cannot declare reserved compose service {NAME}; use manifest service_patches instead": (
        "{SOURCE} не может объявлять зарезервированный compose-сервис {NAME}; используйте service_patches в manifest"
    ),
    "Invalid %s=%r, falling back to system locale": (
        "Недопустимое значение %s=%r, используется системная локаль"
    ),
    "Invalid %s=%r, using system locale %s": (
        "Недопустимое значение %s=%r, используется системная локаль %s"
    ),
    "Invalid debugger backend choice %r, using %s": (
        "Недопустимое значение backend отладчика %r, используется %s"
    ),
    "Invalid local plugin module name: {NAME!r}": (
        "Недопустимое имя локального модуля плагина: {NAME!r}"
    ),
    "Invalid ODPM_IDE choice %r, using %s": (
        "Недопустимое значение ODPM_IDE %r, используется %s"
    ),
    "Invalid {LABEL} odpm.json at {PATH}: {DETAIL}": (
        "Недопустимый {LABEL} odpm.json в {PATH}: {DETAIL}"
    ),
    "Invalid manifest_schema value {VALUE!r}; expected an integer.": (
        "Недопустимое значение manifest_schema {VALUE!r}; ожидается целое число."
    ),
    "Invalid {FIELD} value {VALUE!r}; expected a semantic version "
    "(for example 4.4 or 4.4.0).": (
        "Недопустимое значение {FIELD} {VALUE!r}; ожидается семантическая версия "
        "(например 4.4 или 4.4.0)."
    ),
    "If you want drop this file to default values, just delete it": (
        "Если вы хотите сбросить настройки этого файла в параметры по умолчанию, "
        "просто удалите его."
    ),
    "Hook plugin {PLUGIN_ID} does not implement {METHOD}": (
        "Плагин хука {PLUGIN_ID} не реализует {METHOD}"
    ),
    "Nested {CONFIG_FILE_NAME} at {MANIFEST_PATH} must be a JSON object": (
        "Вложенный {CONFIG_FILE_NAME} ({MANIFEST_PATH}) должен быть JSON-объектом"
    ),
    "Nested odpm.json at {MANIFEST_PATH} declares odoo_version {NESTED_VERSION}, "
    "host project uses {HOST_VERSION}": (
        "Вложенный odpm.json ({MANIFEST_PATH}) задаёт odoo_version {NESTED_VERSION}, "
        "в host-проекте используется {HOST_VERSION}"
    ),
    "Nested odpm.json at {MANIFEST_PATH} declares python_version {NESTED_VERSION}, "
    "host project uses {HOST_VERSION}": (
        "Вложенный odpm.json ({MANIFEST_PATH}) задаёт python_version {NESTED_VERSION}, "
        "в host-проекте используется {HOST_VERSION}"
    ),
    "Manifest at {PATH} is not valid JSON.": (
        "Файл manifest {PATH} не является корректным JSON."
    ),
    "Manifest at {PATH} is valid ({SCHEMA} JSON Schema).": (
        "Манифест {PATH} корректен (JSON Schema {SCHEMA})."
    ),
    "Manifest file not found at {PATH}.": (
        "Файл манифеста не найден: {PATH}."
    ),
    "Manifest hook {PHASE} failed: {COMMAND}": (
        "Manifest hook {PHASE} завершился с ошибкой: {COMMAND}"
    ),
    "Manifest is already manifest_schema 2.": (
        "Манифест уже использует manifest_schema 2."
    ),
    "Manifest root must be a JSON object.": (
        "Корень манифеста должен быть JSON-объектом."
    ),
    "Manifest requires odpm manager {REQUIRES} or newer; "
    "current manager is {ODPM_VERSION}.": (
        "Manifest требует odpm менеджер {REQUIRES} или новее; "
        "текущий менеджер {ODPM_VERSION}."
    ),
    'manifest subcommand required: use "odpm manifest migrate" or '
    '"odpm manifest validate".': (
        'Укажите подкоманду manifest: "odpm manifest migrate" или '
        '"odpm manifest validate".'
    ),
    "manifest locks.git vs deps.lock.json differ: {DETAIL}": (
        "locks.git в manifest и deps.lock.json расходятся: {DETAIL}"
    ),
    "manifest_schema 2 requires requires_odpm (minimum odpm manager version).": (
        "manifest_schema 2 требует поле requires_odpm (минимальная версия менеджера odpm)."
    ),
    "Non-interactive mode cannot prompt to download Odoo platform sources for the "
    "server scenario. Platform directory {odoo_src_dir} is missing odoo-bin. "
    "Pre-install platform sources, run odpm from an interactive terminal, or use "
    "ODPM_SCENARIO=developer for git-based clone during prepare.": (
        "В неинтерактивном режиме нельзя запросить загрузку исходников platform "
        "для сценария server. В каталоге {odoo_src_dir} отсутствует odoo-bin. "
        "Установите исходники заранее, запустите odpm в интерактивном терминале "
        "или используйте ODPM_SCENARIO=developer для git-клонирования на этапе prepare."
    ),
    "Non-interactive mode requires an existing .env file in the project directory "
    "or under ~/.odpm/.env. Create it manually or set environment variables "
    "(BACKUP_DIR, ODOO_PROJECTS_DIR, PATH_TO_SSH_KEY, ODOO_PORT, POSTGRES_PORT, "
    "DEBUGGER_PORT, GEVENT_PORT, ODPM_SCENARIO, ODPM_LOCALE, "
    "ODPM_DEBUGGER_BACKEND, ODPM_IDE) before the first run.": (
        "В неинтерактивном режиме нужен готовый файл .env в каталоге проекта "
        "или ~/.odpm/.env. Создайте его вручную или задайте переменные окружения "
        "(BACKUP_DIR, ODOO_PROJECTS_DIR, PATH_TO_SSH_KEY, ODOO_PORT, POSTGRES_PORT, "
        "DEBUGGER_PORT, GEVENT_PORT, ODPM_SCENARIO, ODPM_LOCALE, "
        "ODPM_DEBUGGER_BACKEND, ODPM_IDE) перед первым запуском."
    ),
    "Non-interactive mode requires odoo_version in the developing project's "
    "odpm.json or pass --odoo-version on the command line.": (
        "В неинтерактивном режиме требуется odoo_version в odpm.json "
        "разрабатываемого проекта или параметр --odoo-version в командной строке."
    ),
    "Platform git repository at {odoo_src_dir} is not ready yet; "
    "cloning will run during prepare (git.materialize step).": (
        "Git-репозиторий platform в {odoo_src_dir} ещё не готов; "
        "клонирование выполнится на этапе prepare (шаг git.materialize)."
    ),
    "Please select scenario by number of odpm usage from this list {LIST_OF_SCENARIOS}\n "
    "Press 'Enter' to leave default value:\n": (
        "Пожалуйта выберите ценарий использования odpm из указанного списка "
        "{LIST_OF_SCENARIOS}\n Нажпите 'Enter' чтобы оставить значение по уполчнию:\n"
    ),
    "Please, enter odoo versions of this project. There is list of supported versions: "
    "{AVAILABEL_ODOO_VERSIONS_ARE}. You can leave default {ODOO_LATEST_VERSION} or "
    "write your own. Press 'Enter' to leave default value:\n": (
        "Пожалуйста, выберите версию Odoo для текущего проекта. "
        "Вот список поддерживаемых версий: {AVAILABEL_ODOO_VERSIONS_ARE}. "
        "Вы можете оставить значение по умолчанию {ODOO_LATEST_VERSION} или написать "
        "свою версию из списка. Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
    ),
    "Pre-commit file {PRE_COMMIT_FILE} was not found at {ODOO_PROJECT_DIR_PATH}": (
        "Pre-commit файл {PRE_COMMIT_FILE} не был найден в каталоге "
        "{ODOO_PROJECT_DIR_PATH}"
    ),
    "Planned changes:": (
        "Планируемые изменения:"
    ),
    "Running with sudo/root privileges is not permitted.": (
        "Запуск скрипта от root/sudo запрещен"
    ),
    "running command: → git {GIT_ARGS} for {PROJECT}": (
        "Выполняется команда: → git {GIT_ARGS} для {PROJECT}"
    ),
    "Skipping developing lock apply in developer scenario; "
    "git state is managed by the developer": (
        "Пропуск применения lock developing в developer-сценарии; "
        "состояние git управляется разработчиком"
    ),
    "Set debugger port which it will listen. You can leave default "
    "{DEFAULT_DEBUGGER_PORT} or write your own. Press 'Enter' to leave default value:\n": (
        "Укажите порт, который будет слушать сервер Отладчик. Можете оставить "
        "значение по умолчанию {DEFAULT_DEBUGGER_PORT} или укажите свой собственный. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
    ),
    "psycopg2 is required.": (
        "Требуется psycopg2."
    ),
    "Recorded database baseline snapshot at {PATH}.": (
        "Записан снимок baseline БД: {PATH}."
    ),
    "Starting PostgreSQL service {SERVICE} for baseline adoption.": (
        "Запуск сервиса PostgreSQL {SERVICE} для принятия baseline."
    ),
    "Set directory for odoo creating/restoring backups, You can leave default "
    "{DEFAULT_ODOO_BACKUP_DIR} or write your own. Press 'Enter' to leave default "
    "value:": (
        "Укажите каталог создания/восстановления бэкапов odoo, Вы можете оставить "
        "значение по умолчанию {DEFAULT_ODOO_BACKUP_DIR} или написать ваше собственное. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:"
    ),
    "Set IDE host name for pydevd_connect (container connects to Debug Server). "
    "Press 'Enter' for default {DEFAULT_HOST}:\n": (
        "Укажите имя хоста IDE для pydevd_connect (контейнер подключается к Debug Server). "
        "Нажмите 'Enter' для значения по умолчанию {DEFAULT_HOST}:\n"
    ),
    "Set gevent port which it will listen. You can leave default {DEFAULT_GEVENT_PORT} "
    "or write your own. Press 'Enter' to leave default value:\n": (
        "Укажите порт, который будет слушать сервер Gevent Websocket. Можете оставить "
        "значение по умолчанию {DEFAULT_GEVENT_PORT} или укажите свой собственный. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
    ),
    "Suspend Odoo until PyCharm Debug Server connects? "
    "Answer y/yes or n/no (Enter for no):\n": (
        "Приостанавливать Odoo до подключения PyCharm Debug Server? "
        "Ответьте y/yes или n/no (Enter — нет):\n"
    ),
    "Set odoo port which it will listen. You can leave default {DEFAULT_ODOO_PORT} or "
    "write your own. Press 'Enter' to leave default value:\n": (
        "Укажите порт, который будет слушать odoo. Можете оставить значение по умолчанию"
        " {DEFAULT_ODOO_PORT} или укажите свой собственный. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
    ),
    "Set odpm host message language. System locale is {SYSTEM_LOCALE}. "
    "Press 'Enter' to keep the system default or type a locale "
    "(for example ru_RU):": (
        "Укажите язык сообщений odpm на host. Локаль системы: {SYSTEM_LOCALE}. "
        "Нажмите 'Enter', чтобы оставить системную локаль, или введите локаль "
        "(например ru_RU):"
    ),
    "Set other odoo projects sources directory, You can leave default "
    "{DEFAULT_ODOO_PROJECTS_SRC_DIR} or write your own. Press 'Enter' to leave "
    "default value:": (
        "Укажите каталог хранения исходных текстов других проектов odoo, Вы можете "
        "оставить значение по умолчанию {DEFAULT_ODOO_PROJECTS_SRC_DIR} или написать "
        "ваше собственное. Нажмите 'Enter' чтобы оставить значение по умолчанию:"
    ),
    "Set PostgreSQL database server port which it will listen. You can leave default "
    "{DEFAULT_POSTGRES_PORT} or write your own. Press 'Enter' to leave default value:\n": (
        "Укажите порт, который будет слушать сервер PostgreSQL. Можете оставить "
        "значение по умолчанию {DEFAULT_POSTGRES_PORT} или укажите свой собственный. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
    ),
    "Switching project {PROJECT_NAME} to branch {BRANCH_NAME}": (
        "Переключение проекта {PROJECT_NAME} на ветку {BRANCH_NAME}"
    ),
    "The {ODOO_GIT_LINK_PARAM} parameter can only be used together with the "
    "{INIT_PARAM} parameter": (
        "Параметр {ODOO_GIT_LINK_PARAM} может использоваться только совместно с "
        "параметром {INIT_PARAM}"
    ),
    "This dir is already {PROJECT_NAME} project": (
        "Данный каталог уже является {PROJECT_NAME} проектом"
    ),
    "To change PostgreSQL major version:\n"
    "1. Stop containers (docker compose down).\n"
    "2. Back up Odoo databases if needed.\n"
    "3. Remove the PostgreSQL data directory: {DATA_PATH}\n"
    "4. Run: odpm --accept-database-drift=postgres_major\n"
    "Alternatively delete {LAST_RUN_REL} and run odpm again.": (
        "Чтобы сменить major-версию PostgreSQL:\n"
        "1. Остановите контейнеры (docker compose down).\n"
        "2. При необходимости сделайте резервную копию баз Odoo.\n"
        "3. Удалите каталог данных PostgreSQL: {DATA_PATH}\n"
        "4. Запустите: odpm --accept-database-drift=postgres_major\n"
        "Либо удалите {LAST_RUN_REL} и снова запустите odpm."
    ),
    "To use a different PostgreSQL data directory:\n"
    "1. Stop containers (docker compose down).\n"
    "2. Move or remove the old data under {PREVIOUS}.\n"
    "3. Run: odpm --accept-database-drift=data_path\n"
    "Current configured path: {CURRENT}.": (
        "Чтобы использовать другой каталог данных PostgreSQL:\n"
        "1. Остановите контейнеры (docker compose down).\n"
        "2. Переместите или удалите старые данные в {PREVIOUS}.\n"
        "3. Запустите: odpm --accept-database-drift=data_path\n"
        "Текущий настроенный путь: {CURRENT}."
    ),
    "Updated database baseline snapshot at {PATH}.": (
        "Обновлён снимок baseline базы данных: {PATH}."
    ),
    'This is not {PROJECT_NAME} directory. If you want to init new project use '
    '"{PROJECT_NAME} {INIT_PARAM}" command': (
        "Данный каталог не является odpm проектом. Если вы хотите создать новый "
        "проект, используйте команду '{PROJECT_NAME} {INIT_PARAM}'. "
    ),
    "Unexpected PostgreSQL connection error: {DETAIL}": (
        "Неожиданная ошибка подключения к PostgreSQL: {DETAIL}"
    ),
    "Unsupported odpm extension API version {VERSION}{LABEL}; "
    "supported versions: {SUPPORTED}.": (
        "Неподдерживаемая версия API расширений odpm {VERSION}{LABEL}; "
        "поддерживаемые версии: {SUPPORTED}."
    ),
    "Unsupported manifest_schema {SCHEMA}.": (
        "Неподдерживаемый manifest_schema {SCHEMA}."
    ),
    "Unsupported manifest_schema {SCHEMA}; this manager supports "
    "manifest_schema up to {MAX_SCHEMA}.": (
        "Неподдерживаемый manifest_schema {SCHEMA}; этот менеджер поддерживает "
        "manifest_schema до {MAX_SCHEMA}."
    ),
    "Unknown ODPM_SCENARIO=%r, using %s": (
        "Неизвестный ODPM_SCENARIO=%r, используется %s"
    ),
    "Unknown manifest hook plugin id: {PLUGIN_ID}": (
        "Неизвестный id плагина manifest hook: {PLUGIN_ID}"
    ),
    "Unsupported odpm.json contract line {CONTRACT}; supported values are "
    "{SUPPORTED}.": (
        "Неподдерживаемая строка контракта odpm.json {CONTRACT}; допустимые "
        "значения: {SUPPORTED}."
    ),
    "Updated PostgreSQL application role {ROLE}.": (
        "Обновлена роль приложения PostgreSQL {ROLE}."
    ),
    "You do not set where developing project is situated. You can set it with --init "
    "command. Example: '--init file:///home/user/projects/your_directory_for_project' or "
    "directly form git repo --init "
    "https://github.com/aayartsev/odoo_demo_project.git'. You also can set it in "
    "user_settings.json file in key 'developing_project'": (
        "Вы не указали разрабатываемый проект. Вы можете указать это при использовании "
        "--init команды. Например: '--init file:///home/user/projects/"
        "your_directory_for_project' или напрямую из git репозитория --init "
        "https://github.com/aayartsev/odoo_demo_project.git'. Вы так же можете указать "
        "это в файле user_settings.json в ключе 'developing_project'"
    ),
    "You need to add your user {CURRENT_USER} to group {LINUX_DOCKER_GROUPNAME} run "
    "this command as root or sudo:  usermod -a -G {LINUX_DOCKER_GROUPNAME} "
    "{CURRENT_USER} then reboot your computer": (
        "Вам необходимо добавить пользователя {CURRENT_USER} в группу "
        "{LINUX_DOCKER_GROUPNAME}\n запустите следующую команду от имени root или с "
        "помощью sudo:  usermod -a -G {LINUX_DOCKER_GROUPNAME} {CURRENT_USER}\n "
        "Затем перезапустите ваш компьютер"
    ),
    "You need to have free space more than {NECESSARY_FREE_SPACE} in {DIR_FOR_FREE_SPACE} "
    "directory": (
        "В каталоге {DIR_FOR_FREE_SPACE} должно быть больше чем {NECESSARY_FREE_SPACE} "
        "свободного места"
    ),
    "You selected the system default locale for odpm messages: {SELECTED_LOCALE}\n": (
        "Вы выбрали системную локаль по умолчанию для сообщений odpm: {SELECTED_LOCALE}\n"
    ),
    "You selected this locale for odpm messages: {SELECTED_LOCALE}\n": (
        "Вы выбрали следующую локаль для сообщений odpm: {SELECTED_LOCALE}\n"
    ),
    "You select {SELECTED_ODPM_SCENARIO} scenario  for odpm usage\n": (
        "Вы выбрали ценарий {SELECTED_ODPM_SCENARIO} для использования odpm\n"
    ),
    "You select this odoo backups dir: {SELECTED_ODOO_BACKUPS_DIR}\n": (
        "Вы выбрали следующий каталог для использования бэкапов odoo: "
        "{SELECTED_ODOO_BACKUPS_DIR}\n"
    ),
    "You select this odoo version: {SELECTED_ODOO_VERSION}\n": (
        "Вы выбрали следующую версию odoo: {SELECTED_ODOO_VERSION}\n"
    ),
    "You select this other odoo projects sources dir: {SELECTED_ODOO_PROJECTS_DIR}\n": (
        "Вы выбрали следующий каталог для хранения исходных текстов других odoo "
        "проектов: {SELECTED_ODOO_PROJECTS_DIR}\n"
    ),
    "You select this port for which Odoo Gevent Websocket System will listen: "
    "{SELECTED_GEVENT_PORT}\n": (
        "Вы выбрали следующий порт, который будет слушать Odoo Gevent Websocket System: "
        "{SELECTED_GEVENT_PORT}\n"
    ),
    "You select this port for which odoo will listen: {SELECTED_ODOO_PORT}\n": (
        "Вы выбрали следующий порт, который будет слушать odoo: {SELECTED_ODOO_PORT}\n"
    ),
    "You select this port for which PostgreSQL database server will listen: "
    "{SELECTED_POSTGRES_PORT}\n": (
        "Вы выбрали следующий порт, который будет слушать сервер PostgreSQL: "
        "{SELECTED_POSTGRES_PORT}\n"
    ),
    "Select debugger backend for developer scenario "
    "(Enter for default {DEFAULT_BACKEND}):\n{OPTIONS}\n": (
        "Выберите backend отладчика для сценария developer "
        "(Enter — по умолчанию {DEFAULT_BACKEND}):\n{OPTIONS}\n"
    ),
    "You selected debugger backend: {SELECTED_BACKEND}\n": (
        "Вы выбрали backend отладчика: {SELECTED_BACKEND}\n"
    ),
    "Select IDE configuration to generate "
    "(Enter for default {DEFAULT_IDE}):\n{OPTIONS}\n": (
        "Выберите конфигурацию IDE для генерации "
        "(Enter — по умолчанию {DEFAULT_IDE}):\n{OPTIONS}\n"
    ),
    "You selected IDE configuration: {SELECTED_IDE}\n": (
        "Вы выбрали конфигурацию IDE: {SELECTED_IDE}\n"
    ),
    "You selected debugger connect host: {SELECTED_HOST}\n": (
        "Вы выбрали хост подключения отладчика: {SELECTED_HOST}\n"
    ),
    "You selected debugger suspend on connect: {SELECTED_SUSPEND}\n": (
        "Вы выбрали приостановку при подключении отладчика: {SELECTED_SUSPEND}\n"
    ),
    "You select this port for which Python Debugger will listen: "
    "{SELECTED_DEBUGGER_PORT}\n": (
        "Вы выбрали следующий порт, который будет слушать Python Debugger: "
        "{SELECTED_DEBUGGER_PORT}\n"
    ),
    "Your odoo src directory {odoo_src_dir} is not git repository.Please fix it, or "
    "delete and clone its repo again: git clone https://github.com/odoo/odoo.git": (
        "Указанный вами каталог с исходными текстами odoo {odoo_src_dir} не является git "
        "репозиторием или репозиторий поврежденПожалуйста исправьте повреждения или "
        "клонируйте репозиторий заново: git clone https://github.com/odoo/odoo.git"
    ),
    "Attached to container output. Detailed technical logs below are in English.": (
        "Подключение к выводу контейнера. Подробные технические логи ниже — на английском."
    ),
    "Check `docker compose ps` and the English log output above for details.": (
        "Проверьте `docker compose ps` и английский лог выше для подробностей."
    ),
    "Checking out {REF} for {PROJECT}": (
        "Переключение на {REF} для {PROJECT}"
    ),
    "Compose stack is healthy; reusing existing containers without --force-recreate": (
        "Стек compose в порядке; перезапуск без --force-recreate"
    ),
    "Container start skipped (--skip-start).": (
        "Запуск контейнеров пропущен (--skip-start)."
    ),
    "Control+C pressed; stopping.": "Нажато Control+C; остановка.",
    "Git dependency lock updated; container start skipped.": (
        "Git dependency lock обновлён; запуск контейнеров пропущен."
    ),
    "Preparing your Odoo environment (dependencies, templates, compose files)...": (
        "Подготовка окружения Odoo (зависимости, шаблоны, compose)..."
    ),
    "Project files are ready.": "Файлы проекта готовы.",
    "Starting containers with Docker Compose...": (
        "Запуск контейнеров через Docker Compose..."
    ),
    "Warnings:": (
        "Предупреждения:"
    ),
    "Wrote .odpm/deps.lock.json; manifest locks.git unchanged "
    "(use --sync-manifest-locks with --update-lock)": (
        "Записан .odpm/deps.lock.json; manifest locks.git не изменён "
        "(используйте --sync-manifest-locks с --update-lock)"
    ),
    "Wrote git dependency lock to {PATH}": (
        "Записан git lock зависимостей в {PATH}"
    ),
    "Wrote locks.git to {PATH}": (
        "Записан locks.git в {PATH}"
    ),
    "Wrote manifest v2 to {PATH}.": (
        "Записан manifest v2 в {PATH}."
    ),
    "When Odoo is ready, open http://localhost:{ODOO_PORT}": (
        "Когда Odoo будет готов, откройте http://localhost:{ODOO_PORT}"
    ),
}

RU_MESSAGES.update(PLAN_L10N_RU)


def _po_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def write_en_po() -> None:
    """Write en_US catalog (msgstr equals msgid; gettext fallback at runtime)."""
    EN_US_PO.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# English host CLI catalog (msgstr mirrors msgid).",
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: odpm\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        '"Language: en_US\\n"',
        "",
    ]
    for msgid in sorted(RU_MESSAGES):
        lines.append(f'msgid "{_po_escape(msgid)}"')
        lines.append(f'msgstr "{_po_escape(msgid)}"')
        lines.append("")
    EN_US_PO.write_text("\n".join(lines), encoding="utf-8")


def write_po() -> None:
    RU_PO.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: odpm\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        '"Language: ru_RU\\n"',
        "",
    ]
    for msgid in sorted(RU_MESSAGES):
        msgstr = RU_MESSAGES[msgid]
        lines.append(f'msgid "{_po_escape(msgid)}"')
        lines.append(f'msgstr "{_po_escape(msgstr)}"')
        lines.append("")
    RU_PO.write_text("\n".join(lines), encoding="utf-8")


def compile_mo() -> None:
    subprocess.run(
        ["msgfmt", "-o", str(RU_MO), str(RU_PO)],
        check=True,
    )


def main() -> int:
    write_po()
    write_en_po()
    compile_mo()
    print(f"Wrote {RU_PO}, {EN_US_PO}, and {RU_MO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
