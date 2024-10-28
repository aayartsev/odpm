import os
import platform

ARCH = str(platform.machine()).lower()
DEV_PROJECT_DIR = "dev_project"
CONFIG_FILE_NAME = "config.json"

PROJECT_NAME = "odpm"
PROJECT_CONFIG_FILE_NAME = f"{PROJECT_NAME.lower()}.json"
USER_CONFIG_FILE_NAME = "user_settings.json"
CONFIG_DIR_IN_HOME_DIR = f".{PROJECT_NAME.lower()}"
PROJECT_SERVICE_DIRECTORY = f".{PROJECT_NAME.lower()}"
ENV_FILE_NAME = ".env"
DOCKERFILE = "Dockerfile"
ODOO_CONF_NAME = "odoo.conf"

PROGRAM_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH = os.path.join(DEV_PROJECT_DIR, "templates", "docker-compose.yml")
PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "docker-compose.yml")

PROGRAM_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH = os.path.join(DEV_PROJECT_DIR, "templates", "dev_odoo_docker_config_file.conf")
PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "dev_odoo_docker_config_file.conf")

PROGRAM_VSCODE_SETTINGS_TEMPLATE = os.path.join(DEV_PROJECT_DIR, "templates", "vscode_settings.json")
PROJECT_VSCODE_SETTINGS_TEMPLATE = os.path.join(PROJECT_SERVICE_DIRECTORY, "vscode_settings.json")

DATABASE_NAME_INSTANCE = "db"
DEBUGGER_DEFAULT_PORT = 5678
DEBUGGER_DOCKER_PORT = DEBUGGER_DEFAULT_PORT
ODOO_DEFAULT_PORT = 8069
ODOO_DOCKER_PORT = ODOO_DEFAULT_PORT
POSTGRES_DEFAULT_PORT = 5432
POSTGRES_DOCKER_PORT = POSTGRES_DEFAULT_PORT
DEBUGGER_UNIT_NAME = "Odoo: Remote Attach"
GITLINK_TYPE_GIT = "git"
GITLINK_TYPE_HTTP = "http"
GITLINK_TYPE_SSH = "ssh"
GITLINK_TYPE_FILE = "local_filesystem"
TYPE_PROJECT_PROJECT = "project"
TYPE_PROJECT_MODULE = "module"
CURRENT_USER_UID = "9999"
CURRENT_USER_GID = CURRENT_USER_UID
CURRENT_USER = "odoo"
CURRENT_PASSWORD = CURRENT_USER
LINUX_DOCKER_GROUPNAME = "docker"
if ARCH == "x86_64":
    ARCH = "amd64"
if ARCH == "aarch64":
    ARCH = "arm64"

if platform.system() == "Linux":
    import pwd
    CURRENT_USER_UID = os.getuid()
    CURRENT_USER_GID = os.getgid()
    CURRENT_USER = pwd.getpwuid(CURRENT_USER_UID)[0]

# If you have already used this image of postgres, you can have situation when your variables are not enabled
# https://github.com/docker-library/docs/blob/master/postgres/README.md
# Warning: the Docker specific variables will only have an effect if you start the container with a data directory that is empty; any pre-existing database will be left untouched on container startup.
# In this case you need to delete old data or use old variables
POSTGRES_ODOO_USER = CURRENT_USER
POSTGRES_ODOO_PASS = CURRENT_PASSWORD
POSTGRES_ODOO_HOST = DATABASE_NAME_INSTANCE
POSTGRES_ODOO_PORT = POSTGRES_DOCKER_PORT

NO_LOG_PREFIX = "--no-log-prefix"
DOCKER_COMPOSE_DEFAULT_FILE_VERSION = "3.3"

DOCKER_WORKING_MESSAGE = "Server Version"
GIT_WORKING_MESSAGE = "git version"
DOCKER_COMPOSE_WORKING_MESSAGE = "docker compose version"

MESSAGE_MARKER = "#MESSAGE#"
ADMIN_PASSWD_MESSAGE = "#ADMIN_PASSWD_MESSAGE#"
DO_NOT_CHANGE_PARAM = "#DO_NOT_CHANGE_PARAM#"
POSTGRES_ODOO_USER_MARKER = "#POSTGRES_ODOO_USER_MARKER#"
POSTGRES_ODOO_PASS_MARKER = "#POSTGRES_ODOO_PASS_MARKER#"
POSTGRES_ODOO_HOST_MARKER = "#POSTGRES_ODOO_HOST_MARKER#"
POSTGRES_ODOO_PORT_MARKER = "#POSTGRES_ODOO_PORT_MARKER#"
ODOO_PORT_MARKER = "#ODOO_PORT_MARKER#"

ODOO_GIT_LINK = "https://github.com/odoo/odoo.git"

DEFAULT_DEBUGPY = "debugpy==1.6.3"
DEBUGPY = {
    "3.7": DEFAULT_DEBUGPY,
    "3.8": DEFAULT_DEBUGPY,
    "3.9": DEFAULT_DEBUGPY,
    "3.10": "debugpy==1.7.0",
    "3.11": "debugpy==1.7.0",
    "3.12": "debugpy==1.7.0",
}

DEFAULT_POSTGRES_VERSION = "13"
DEFAULT_PYTHON_VERSION = "3.7"
DEFAULT_DISTRO_NAME = "debian"
DEFAULT_DISTRO_VERSION = "11"
DISTRO_INFO = {
    "debian":{
        "11": "bullseye",
        "12": "bookworm",
    },
    "ubuntu":{
        "22.04": "jammy",
        "20.04": "focal",
    }
}

# git rev-parse --abbrev-ref HEAD
ODOO_LATEST_VERSION = "18.0"
ODOO_VERSION_DEFAULT_ENV = {
    "18.0": {
        "python_version": "3.10",
        "distro_name": "bookworm",
        "distro_version": "12",
    },
    "17.0": {
        "python_version": "3.10",
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "16.0": {
        "python_version": "3.10",
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "15.0": {
        "python_version": DEFAULT_PYTHON_VERSION,
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "14.0": {
        "python_version": DEFAULT_PYTHON_VERSION,
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "13.0": {
        "python_version": DEFAULT_PYTHON_VERSION,
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "12.0": {
        "python_version": DEFAULT_PYTHON_VERSION,
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
    "11.0": {
        "python_version": DEFAULT_PYTHON_VERSION,
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": DEFAULT_DISTRO_VERSION,
    },
}

DEFAULT_LOCALE = "en_US"

MODULE_FILES = ("__manifest__.py", "__openerp__.py", "__odoo__.py", "__terp__.py")

DEPRECATED_WORDS = [
    "debian_version",
    "debian_name"
]

####
# Default user_settings.json values
####
DEFAULT_LIST_OF_MODULES = ""
DEFAULT_INIT_MODULES = DEFAULT_LIST_OF_MODULES
DEFAULT_UPDATE_MODULES = DEFAULT_LIST_OF_MODULES
# Default values for database creation
DEFAULT_DB_CREATION_DATA_DB_LANG = "en_US"
DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE = None
DEFAULT_DB_CREATION_DATA_CREATE_DEMO = True
DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_LOGIN = "admin"
DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_PASSWORD = "admin"

DEFAULT_DB_CREATION_DATA = {}
DEFAULT_UPDATE_GIT_REPOS = False
DEFAULT_CLEAN_GIT_REPOS = False
DEFAULT_CHECK_SYSTEM = False
DEFAULT_DB_MANAGER_PASSWORD = "1"
DEFAULT_DEV_MODE = False
DEFAULT_DEVELOPING_PROJECT = ""
DEFAULT_PRE_COMMIT_MAP_FILES = []
DEFAULT_SQL_QUERIES = []
DEFAULT_USE_OCA_DEPENDENCIES = False
DEFAULT_CREATE_MODULE_LINKS = False

# YANDEX DISK LINKS
YADISK_SHARING_LINK = "https://disk.yandex.ru/d/-5z2VJ_DUo2v2g"
YADISK_API_ENDPOINT = "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}"

FREE_SPACE_FOR_USAGE = 20.0
