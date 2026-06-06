import os
import platform

ARCH = str(platform.machine()).lower()

DATABASE_NAME_INSTANCE = "db"
DEBUGGER_DEFAULT_PORT = 5678
DEBUGGER_DOCKER_PORT = DEBUGGER_DEFAULT_PORT
ODOO_DEFAULT_PORT = 8069
ODOO_DOCKER_PORT = ODOO_DEFAULT_PORT
POSTGRES_DEFAULT_PORT = 5432
POSTGRES_DOCKER_PORT = POSTGRES_DEFAULT_PORT
GEVENT_DEFAULT_PORT = 8072
GEVENT_DOCKER_PORT = GEVENT_DEFAULT_PORT

DEBUGGER_UNIT_NAME = "Odoo: Remote Attach"
GITLINK_TYPE_GIT = "git"
GITLINK_TYPE_HTTP = "http"
GITLINK_TYPE_SSH = "ssh"
GITLINK_TYPE_FILE = "local_filesystem"
TYPE_PROJECT_PROJECT = "project"
TYPE_PROJECT_MODULE = "module"

# Identity inside Odoo/Postgres Docker containers (never tied to the host login).
CONTAINER_USER_UID = "9999"
CONTAINER_USER_GID = CONTAINER_USER_UID
CONTAINER_USER = "odoo"
CONTAINER_PASSWORD = CONTAINER_USER

# Host OS user (Linux: real uid/name for docker group checks and permissions).
HOST_USER = CONTAINER_USER
HOST_USER_UID = CONTAINER_USER_UID
HOST_USER_GID = CONTAINER_USER_GID

LINUX_DOCKER_GROUPNAME = "docker"
if ARCH == "x86_64":
    ARCH = "amd64"
if ARCH == "aarch64":
    ARCH = "arm64"

if platform.system() == "Linux":
    import pwd

    HOST_USER_UID = os.getuid()
    HOST_USER_GID = os.getgid()
    HOST_USER = pwd.getpwuid(HOST_USER_UID)[0]

# Backward-compatible aliases for container identity (always odoo / 9999).
CURRENT_USER_UID = CONTAINER_USER_UID
CURRENT_USER_GID = CONTAINER_USER_GID
CURRENT_USER = CONTAINER_USER
CURRENT_PASSWORD = CONTAINER_PASSWORD
# https://github.com/docker-library/docs/blob/master/postgres/README.md
# Warning: the Docker specific variables will only have an effect if you start the container with a data directory that is empty; any pre-existing database will be left untouched on container startup.
# In this case you need to delete old data or use old variables
POSTGRES_ODOO_USER = CONTAINER_USER
POSTGRES_ODOO_PASS = CONTAINER_PASSWORD
POSTGRES_ODOO_HOST = DATABASE_NAME_INSTANCE
POSTGRES_ODOO_PORT = POSTGRES_DOCKER_PORT

DOCKER_WORKING_MESSAGE = "Version"
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

ODOO_CONFIG_TEMPLATE_MARKERS = [
    DO_NOT_CHANGE_PARAM,
    ADMIN_PASSWD_MESSAGE,
    POSTGRES_ODOO_USER_MARKER,
    POSTGRES_ODOO_PASS_MARKER,
    POSTGRES_ODOO_HOST_MARKER,
    POSTGRES_ODOO_PORT_MARKER,
    ODOO_PORT_MARKER,
]

ODOO_GIT_LINK = "https://github.com/odoo/odoo.git"
ODOO_DEFAULT_BUILD_DATE = "latest"

# Platform git: keep shallow clone; extend history only for odoo_build_date checkout.
PLATFORM_GIT_CLONE_DEPTH = 1
PLATFORM_BUILD_DATE_SHALLOW_SINCE_DAYS = 31
PLATFORM_BUILD_DATE_FETCH_DEEPEN_STEP = 500
PLATFORM_BUILD_DATE_FETCH_DEEPEN_MAX = 10000

DEFAULT_DEBUGPY = "debugpy==1.6.3"
DEBUGPY = {
    "3.7": DEFAULT_DEBUGPY,
    "3.8": DEFAULT_DEBUGPY,
    "3.9": DEFAULT_DEBUGPY,
    "3.10": "debugpy==1.7.0",
    "3.11": "debugpy==1.7.0",
    "3.12": "debugpy==1.7.0",
    "3.13": "debugpy==1.8.0",
}

DEFAULT_VENV_BOOTSTRAP = [
    "cython<3.0",
    "wheel",
]
VENV_BOOTSTRAP_PACKAGES = {
    "3.7": ["cython<3.0", "setuptools==59.6.0", "wheel"],
    "3.8": ["cython<3.0", "setuptools==59.6.0", "wheel"],
    "3.9": ["cython<3.0", "setuptools==65.5.0", "wheel"],
    "3.10": ["setuptools==69.5.1", "cython<3.0", "wheel<0.46"],
    "3.11": ["cython<3.0", "setuptools==75.1.0", "wheel"],
    "3.12": ["cython<3.0", "setuptools==75.1.0", "wheel"],
    "3.13": ["cython<3.0", "setuptools==80", "wheel"],
}

DEFAULT_POSTGRES_VERSION = "13"
DEFAULT_PYTHON_VERSION = "3.7"
DEFAULT_DISTRO_NAME = "debian"
DEFAULT_DISTRO_VERSION = "11"
DISTRO_INFO = {
    "debian": {
        "11": "bullseye",
        "12": "bookworm",
        "13": "trixie",
    },
    "ubuntu": {
        "22.04": "jammy",
        "20.04": "focal",
    },
}

# git rev-parse --abbrev-ref HEAD
ODOO_LATEST_VERSION = "19.0"
ODOO_VERSION_DEFAULT_ENV = {
    "19.0": {
        "python_version": "3.12",
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": "13",
    },
    "18.0": {
        "python_version": "3.12",
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": "13",
    },
    "17.0": {
        "python_version": "3.10",
        "distro_name": DEFAULT_DISTRO_NAME,
        "distro_version": "12",
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
# Odoo ``--dev`` features (comma-separated in user_settings.json ``dev_mode``).
# ``all`` is an alias for xml,reload,qweb,access on Odoo 19+ (see Odoo CLI docs).
ODOO_DEV_MODE_ALL = "all"
ODOO_DEV_MODE_FEATURES = ("reload", "qweb", "werkzeug", "xml", "access")
# Odoo autoreload (--dev=reload|all) on Linux uses the PyPI ``inotify`` package.
ODOO_AUTORELOAD_PACKAGE_NAMES = ("inotify", "watchdog")
ODOO_AUTORELOAD_INOTIFY_REQUIREMENT = "inotify"
DEFAULT_DEVELOPING_PROJECT = ""
DEFAULT_PRE_COMMIT_MAP_FILES = []
DEFAULT_SQL_QUERIES = []
DEFAULT_USE_OCA_DEPENDENCIES = False
DEFAULT_CREATE_MODULE_LINKS = False

# YANDEX DISK LINKS
YADISK_SHARING_LINK = "https://disk.yandex.ru/d/FbMn-ySeNYGAoQ"
YADISK_API_ENDPOINT = (
    "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}"
)

FREE_SPACE_FOR_USAGE = 2.0

VENV_LOCK_KEYS = (
    "python_version",
    "distro_version",
    "distro_name",
    "postgres_version",
    "odoo_version",
    "arch",
    "requirements_txt",
    "venv_mode",
)
