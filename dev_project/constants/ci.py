import os

from .paths import DEV_PROJECT_DIR, PROJECT_SERVICE_DIRECTORY

CI_BUILD_CONTEXT_DIR = os.path.join(PROJECT_SERVICE_DIRECTORY, "ci-build-context")
CI_VENV_SPEC_DIR = "ci"
CI_VENV_INSTALL_JSON = os.path.join(CI_VENV_SPEC_DIR, "venv_install.json")
RUN_ODOO_ENTRYPOINT = "dev_project.inside_docker_app.run_odoo"
RUN_WITH_PYDEVD_ENTRYPOINT = "dev_project.inside_docker_app.run_with_pydevd"
RUN_PRE_COMMIT_ENTRYPOINT = "dev_project.inside_docker_app.run_pre_commit"
ODPM_RUNTIME_CONFIG_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "runtime", "config.json")
ODPM_DEBUG_PROFILE_REL_PATH = os.path.join(
    PROJECT_SERVICE_DIRECTORY, "runtime", "debug-profile.json"
)
ODPM_SECRETS_SOURCE_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "secrets.json")
ODPM_SECRETS_EXAMPLE_REL_PATH = os.path.join(
    PROJECT_SERVICE_DIRECTORY, "secrets.example.json"
)
ODPM_SECRETS_RUNTIME_REL_PATH = os.path.join(
    PROJECT_SERVICE_DIRECTORY, "runtime", "secrets.json"
)
ODPM_SECRETS_CONTAINER_PATH = "/run/odpm/secrets.json"
ODPM_SECRETS_PATH_ENV = "ODPM_SECRETS_PATH"
ODPM_RUNTIME_CONFIG_CONTAINER_PATH = "/run/odpm/config.json"
ODPM_CONFIG_PATH_ENV = "ODPM_CONFIG_PATH"
ODPM_RUNTIME_DIR_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "runtime")
ODPM_DATABASE_DIR_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "database")
ODPM_DATABASE_LAST_RUN_REL_PATH = os.path.join(
    ODPM_DATABASE_DIR_REL_PATH, "last_run.json"
)
ODPM_DATABASE_CONTAINER_DIR = "/run/odpm/database"
ODPM_DATABASE_LAST_RUN_CONTAINER_PATH = os.path.join(
    ODPM_DATABASE_CONTAINER_DIR, "last_run.json"
)
CI_RUNTIME_CONFIG_CONTEXT_REL_PATH = os.path.join("runtime", "config.json")
CI_DOCKERFILE = "Dockerfile.ci"
CI_DOCKERFILE_TEMPLATE = os.path.join(DEV_PROJECT_DIR, "templates", "dockerfile_ci")
# Subdirectories omitted when copying dev_project/ into CI build context.
CI_DEV_PROJECT_COPY_IGNORE_DIRS = frozenset(
    {"templates", "i18n", "__pycache__", ".git", "plugins"}
)
