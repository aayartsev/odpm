"""Russian catalog entries for odpm plan / secrets i18n (Phase L gap closure)."""

PLAN_L10N_RU: dict[str, str] = {
    "--sync-manifest-locks is only supported in developer scenario": (
        "--sync-manifest-locks поддерживается только в developer-сценарии"
    ),
    "Apply pinned commits from {SOURCE} before checkout": (
        "Применить закреплённые коммиты из {SOURCE} перед checkout"
    ),
    "Build CI Docker image from prepared context": (
        "Собрать CI Docker-образ из подготовленного контекста"
    ),
    "Build compose start command and write .odpm/runtime/config.json when stale": (
        "Собрать команду запуска compose и записать .odpm/runtime/config.json при устаревании"
    ),
    "Build docker volume mapping for Odoo, venv, and addons": (
        "Построить маппинг docker-томов для Odoo, venv и аддонов"
    ),
    "Check Docker engine": "Проверить Docker engine",
    "Checkout dependency repos to odoo version branch": (
        "Переключить репозитории зависимостей на ветку версии Odoo"
    ),
    "Clone or update platform, developing, and dependency git repos": (
        "Клонировать или обновить platform, developing и git-зависимости"
    ),
    "Clone or update manifest service_sources git repositories": (
        "Клонировать или обновить git-репозитории service_sources из manifest"
    ),
    "Collect resolved git commits and write .odpm/deps.lock.json": (
        "Собрать разрешённые git-коммиты и записать .odpm/deps.lock.json"
    ),
    "Docker compose command is not configured; stack health was not probed": (
        "Команда docker compose не настроена; состояние стека не проверялось"
    ),
    "Invalid .odpm/deps.lock.json; lock verify step omitted from plan": (
        "Некорректный .odpm/deps.lock.json; шаг проверки lock исключён из плана"
    ),
    "Load git lock from {SOURCE} and enter apply mode before checkout": (
        "Загрузить git lock из {SOURCE} и включить режим apply перед checkout"
    ),
    "Apply manifest compose patch to service {NAME}": (
        "Применить compose patch из manifest к сервису {NAME}"
    ),
    "Materialize .odpm/runtime/secrets.json from .odpm/secrets.json": (
        "Материализовать .odpm/runtime/secrets.json из .odpm/secrets.json"
    ),
    "Materialize compose fragment for service {NAME}": (
        "Материализовать compose-фрагмент для сервиса {NAME}"
    ),
    "Materialize manifest and plugin compose service fragments": (
        "Материализовать compose-фрагменты из manifest и плагинов"
    ),
    "PyCharm run configuration already present": (
        "Конфигурация запуска PyCharm уже присутствует"
    ),
    "Refresh project symlinks for local codebase access": (
        "Обновить симлинки проекта для локального доступа к коду"
    ),
    "Regenerate project Dockerfile from odpm template": (
        "Перегенерировать Dockerfile проекта из шаблона odpm"
    ),
    "Regenerate project odoo.conf from .odpm template": (
        "Перегенерировать odoo.conf проекта из шаблона .odpm"
    ),
    "Regenerate root .dockerignore from .odpm/dockerignore": (
        "Перегенерировать корневой .dockerignore из .odpm/dockerignore"
    ),
    "Render docker-compose.yml from project template": (
        "Сгенерировать docker-compose.yml из шаблона проекта"
    ),
    "Run docker compose up": "Запустить docker compose up",
    "Run manifest {PHASE} lifecycle hooks": (
        "Выполнить lifecycle hooks manifest ({PHASE})"
    ),
    "Stop containers occupying odpm ports": (
        "Остановить контейнеры, занимающие порты odpm"
    ),
    "Unknown ODPM_DEBUGGER_BACKEND=%r, using %s": (
        "Неизвестный ODPM_DEBUGGER_BACKEND=%r, используется %s"
    ),
    "Unknown ODPM_DEBUGGER_SUSPEND=%r, using false": (
        "Неизвестный ODPM_DEBUGGER_SUSPEND=%r, используется false"
    ),
    "Unknown ODPM_IDE=%r, using %s": "Неизвестный ODPM_IDE=%r, используется %s",
    "Update VS Code launch and workspace settings": (
        "Обновить launch и workspace settings VS Code"
    ),
    "Upgrade .odpm/docker-compose.yml project template": (
        "Обновить шаблон .odpm/docker-compose.yml проекта"
    ),
    "VS Code settings already present": "Настройки VS Code уже присутствуют",
    "Validate generated docker-compose.yml": (
        "Проверить сгенерированный docker-compose.yml"
    ),
    "Verify checked-out commits match {SOURCE}": (
        "Проверить, что checkout соответствует {SOURCE}"
    ),
    "Verify local platform and developing git directories exist": (
        "Проверить наличие локальных каталогов platform и developing"
    ),
    "Write .odpm/runtime/debug-profile.json": (
        "Записать .odpm/runtime/debug-profile.json"
    ),
    "apply pinned commits from {SOURCE}": (
        "применить закреплённые коммиты из {SOURCE}"
    ),
    "base image identity mismatch": "несовпадение идентичности базового образа",
    "build CI image from prepared context": (
        "собрать CI-образ из подготовленного контекста"
    ),
    "build compose service for compose.generate ({REASON})": (
        "собрать compose service для compose.generate ({REASON})"
    ),
    "cannot read secrets file {PATH}: {DETAIL}": (
        "не удалось прочитать файл secrets {PATH}: {DETAIL}"
    ),
    "check_system disabled; Docker check skipped": (
        "check_system отключён; проверка Docker пропущена"
    ),
    "checkout dependency repos": "переключить репозитории зависимостей",
    "clone or update git repos": "клонировать или обновить git-репозитории",
    "compose fragment {NAME} stale": "compose-фрагмент {NAME} устарел",
    "compose fragment {NAME} up to date": "compose-фрагмент {NAME} актуален",
    "compose service fragments cleanup": "очистка compose service fragments",
    "compose service fragments stale": "compose service fragments устарели",
    "compose service fragments up to date": "compose service fragments актуальны",
    "compose template stale": "шаблон compose устарел",
    "compose template up to date": "шаблон compose актуален",
    "patch keys: {KEYS}": "ключи patch: {KEYS}",
    "compose validation disabled by policy": (
        "валидация compose отключена политикой"
    ),
    "deps.lock will be updated; manifest locks.git unchanged (use --sync-manifest-locks with --update-lock)": (
        "deps.lock будет обновлён; manifest locks.git без изменений "
        "(используйте --sync-manifest-locks с --update-lock)"
    ),
    "deps.lock.json": "deps.lock.json",
    "dockerfile template stale": "шаблон Dockerfile устарел",
    "dockerfile template up to date": "шаблон Dockerfile актуален",
    "dockerignore template stale": "шаблон dockerignore устарел",
    "dockerignore template up to date": "шаблон dockerignore актуален",
    "free odoo, debugger, postgres, and gevent ports before compose up": (
        "освободить порты odoo, debugger, postgres и gevent перед compose up"
    ),
    "git repos will be materialized": "git-репозитории будут материализованы",
    "inject service_sources paths into env resolver": (
        "подставить пути service_sources в env resolver"
    ),
    "invalid JSON in secrets file {PATH}: {DETAIL}": (
        "некорректный JSON в файле secrets {PATH}: {DETAIL}"
    ),
    "load git lock from {SOURCE} before checkout": (
        "загрузить git lock из {SOURCE} перед checkout"
    ),
    "lock apply not used in this mode": "применение lock не используется в этом режиме",
    "lock verify not applicable": "проверка lock не применима",
    "manifest locks.git": "manifest locks.git",
    "materialize repos before writing deps.lock": (
        "материализовать репозитории перед записью deps.lock"
    ),
    "no git lock source available": "источник git lock недоступен",
    "no service_sources declared": "service_sources не объявлены",
    "no {PHASE} hooks configured": "hooks {PHASE} не настроены",
    "odoo config template stale": "шаблон конфигурации Odoo устарел",
    "odoo.conf and template up to date": "odoo.conf и шаблон актуальны",
    "odoo.conf missing db settings": "в odoo.conf отсутствуют настройки БД",
    "only used with --update-lock": "используется только с --update-lock",
    "plugins: {PLUGIN_LIST}": "плагины: {PLUGIN_LIST}",
    "port release runs only in developer scenario": (
        "освобождение портов только в developer-сценарии"
    ),
    "refresh VS Code launch and settings": (
        "обновить launch и settings VS Code"
    ),
    "refresh docker volume mapping": "обновить маппинг docker-томов",
    "refresh project symlinks": "обновить симлинки проекта",
    "secret value for {KEY} must be a string": (
        "значение secret для {KEY} должно быть строкой"
    ),
    "secrets file must be a JSON object": (
        "файл secrets должен быть JSON-объектом"
    ),
    "secrets file must contain a 'secrets' object": (
        "файл secrets должен содержать объект 'secrets'"
    ),
    "secrets file not found: {PATH}": "файл secrets не найден: {PATH}",
    "secrets keys must be non-empty strings": (
        "ключи secrets должны быть непустыми строками"
    ),
    "secrets mount disabled for CI scenario": (
        "монтирование secrets отключено для CI-сценария"
    ),
    "skipped with --no-git-update": "пропущено с --no-git-update",
    "service_sources stale or missing": "service_sources устарели или отсутствуют",
    "service_sources up to date": "service_sources актуальны",
    "skipped with --update-lock": "пропущено с --update-lock",
    "start compose stack (--force-recreate unknown without docker probe)": (
        "запуск compose-стека (--force-recreate неизвестен без docker probe)"
    ),
    "start compose stack (--force-recreate unknown; docker compose command unset)": (
        "запуск compose-стека (--force-recreate неизвестен; команда docker compose не задана)"
    ),
    "start compose stack with --force-recreate (stack missing or unhealthy)": (
        "запуск compose-стека с --force-recreate (стек отсутствует или нездоров)"
    ),
    "start compose stack without --force-recreate (stack healthy)": (
        "запуск compose-стека без --force-recreate (стек здоров)"
    ),
    "unsupported secrets schema_version: {VERSION} (expected {EXPECTED})": (
        "неподдерживаемый secrets schema_version: {VERSION} (ожидается {EXPECTED})"
    ),
    "validate docker-compose.yml": "проверить docker-compose.yml",
    "verify Docker engine": "проверить Docker engine",
    "verify checked-out commits match {SOURCE}": (
        "проверить соответствие checkout {SOURCE}"
    ),
    "verify local git directories exist": (
        "проверить наличие локальных git-каталогов"
    ),
    "verify service_sources paths exist": (
        "проверить наличие путей service_sources"
    ),
    "write deps.lock.json from resolved commits": (
        "записать deps.lock.json из разрешённых коммитов"
    ),
    "{COUNT} shell command(s)": "{COUNT} shell-команда(ы)",
    "Compose stack health was not probed; --force-recreate is unknown": (
        "Состояние compose-стека не проверялось; --force-recreate неизвестен"
    ),
    "debug profile missing": "отсутствует debug profile",
    "debug profile on disk": "debug profile на диске",
    "debug profile payload changed": "изменился payload debug profile",
    "debug profile unchanged": "debug profile без изменений",
    "docker-compose.yml differs from preview": (
        "docker-compose.yml отличается от preview"
    ),
    "docker-compose.yml matches preview": (
        "docker-compose.yml соответствует preview"
    ),
    "docker-compose.yml missing": "отсутствует docker-compose.yml",
    "docker-compose.yml present; full preview needs volume map": (
        "docker-compose.yml присутствует; полный preview требует volume map"
    ),
    "no secrets source": "нет источника secrets",
    "remove stale runtime secrets": "удалить устаревшие runtime secrets",
    "runtime secrets missing": "отсутствуют runtime secrets",
    "secrets runtime up to date": "runtime secrets актуальны",
    "secrets source changed": "источник secrets изменился",
    ".odpm/secrets.json exists but is not listed in .odpm/.gitignore; risk of accidental commit": (
        "файл .odpm/secrets.json существует, но не указан в .odpm/.gitignore; "
        "риск случайного коммита"
    ),
    "compose start command changed": "изменилась команда запуска compose",
    "runtime config and start command unchanged": (
        "runtime config и команда запуска без изменений"
    ),
    "runtime config payload changed": "изменился payload runtime config",
    "unable to preview debug profile": "не удалось построить preview debug profile",
    "venv_lock_hash changed": "изменился venv_lock_hash",
    "Update PyCharm Debug Server run configuration": (
        "Обновить run configuration PyCharm Debug Server"
    ),
    "Update PyCharm Attach to DAP run configuration": (
        "Обновить run configuration PyCharm Attach to DAP"
    ),
    "first database run (no last_run snapshot yet)": (
        "первый запуск БД (снимок last_run ещё не создан)"
    ),
    "database configuration matches last_run snapshot": (
        "конфигурация БД соответствует снимку last_run"
    ),
    "database configuration drift detected: {KINDS}": (
        "обнаружен дрейф конфигурации БД: {KINDS}"
    ),
    "odoo.conf db_host out of sync with postgres service ({EXPECTED})": (
        "В odoo.conf db_host не синхронизирован с сервисом postgres ({EXPECTED})"
    ),
    "Interactive input is not available in non-interactive mode.": (
        "Интерактивный ввод недоступен в неинтерактивном режиме."
    ),
    "System checker is not attached to CreateProjectEnvironment": (
        "Системная проверка окружения не подключена к проекту."
    ),
}
