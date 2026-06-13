#!/usr/bin/env python3
"""Regenerate dev_project i18n catalogs from the embedded message table."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "dev_project" / "i18n"
RU_PO = I18N_DIR / "ru_RU" / "LC_MESSAGES" / "main.po"
RU_MO = I18N_DIR / "ru_RU" / "LC_MESSAGES" / "main.mo"

# msgid (English) -> msgstr (Russian). Keep sorted by msgid for review.
RU_MESSAGES: dict[str, str] = {
    "--build-image is only allowed when ODPM_SCENARIO=ci in .env": (
        "--build-image доступен только при ODPM_SCENARIO=ci в .env"
    ),
    ' "config.json" is deprecated. Please read documentation': (
        ' Файл с параметрами "config.json" является устаревшим. '
        "Пожалуйста обратитесь к документации "
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
    "Created {ENV_FILE} from environment variables and defaults (non-interactive mode).": (
        "Создан файл {ENV_FILE} из переменных окружения и значений по умолчанию "
        "(неинтерактивный режим)."
    ),
    "Did you install git?": "Вы установили git?",
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
    "If you want drop this file to default values, just delete it": (
        "Если вы хотите сбросить настройки этого файла в параметры по умолчанию, "
        "просто удалите его."
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
    "Running with sudo/root privileges is not permitted.": (
        "Запуск скрипта от root/sudo запрещен"
    ),
    "running command: → git {GIT_ARGS} for {PROJECT}": (
        "Выполняется команда: → git {GIT_ARGS} для {PROJECT}"
    ),
    "Set debugger port which it will listen. You can leave default "
    "{DEFAULT_DEBUGGER_PORT} or write your own. Press 'Enter' to leave default value:\n": (
        "Укажите порт, который будет слушать сервер Отладчик. Можете оставить "
        "значение по умолчанию {DEFAULT_DEBUGGER_PORT} или укажите свой собственный. "
        "Нажмите 'Enter' чтобы оставить значение по умолчанию:\n"
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
    'This is not {PROJECT_NAME} directory. If you want to init new project use '
    '"{PROJECT_NAME} {INIT_PARAM}" command': (
        "Данный каталог не является odpm проектом. Если вы хотите создать новый "
        "проект, используйте команду '{PROJECT_NAME} {INIT_PARAM}'. "
    ),
    "Version mismatch: The project requires an older version of odpm - "
    "{PROJECT_ODPM_VERSION}  than your current manager-{ODPM_VERSION}. Please switch "
    "to a manager version compatible with the project.": (
        "Версия odpm используемая в проекте - {PROJECT_ODPM_VERSION} меньше чем "
        "текущия версия менеджера odpm - {ODPM_VERSION}, пожалуйста используйте "
        "версию менеджера соотвествующую версии odpm в проекте. Или созданй новый "
        "проект"
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
    "When Odoo is ready, open http://localhost:{ODOO_PORT}": (
        "Когда Odoo будет готов, откройте http://localhost:{ODOO_PORT}"
    ),
}


def _po_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
    compile_mo()
    print(f"Wrote {RU_PO} and {RU_MO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
