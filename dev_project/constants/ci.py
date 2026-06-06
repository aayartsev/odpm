import os

from .paths import DEV_PROJECT_DIR, PROJECT_SERVICE_DIRECTORY

CI_BUILD_CONTEXT_DIR = os.path.join(PROJECT_SERVICE_DIRECTORY, "ci-build-context")
CI_VENV_SPEC_DIR = "ci"
CI_VENV_INSTALL_JSON = os.path.join(CI_VENV_SPEC_DIR, "venv_install.json")
DEV_ENTRYPOINT = "dev_project.inside_docker_app.main"  # deprecated; use RUN_ODOO_ENTRYPOINT
RUN_ODOO_ENTRYPOINT = "dev_project.inside_docker_app.run_odoo"
ODPM_CONFIG_B64_ENV = "ODPM_CONFIG_B64"
ODPM_RUNTIME_CONFIG_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "runtime", "config.json")
ODPM_RUNTIME_CONFIG_CONTAINER_PATH = "/run/odpm/config.json"
ODPM_CONFIG_PATH_ENV = "ODPM_CONFIG_PATH"
ODPM_RUNTIME_DIR_REL_PATH = os.path.join(PROJECT_SERVICE_DIRECTORY, "runtime")
CI_RUNTIME_CONFIG_CONTEXT_REL_PATH = os.path.join("runtime", "config.json")
CI_DOCKERFILE = "Dockerfile.ci"
CI_DOCKERFILE_TEMPLATE = os.path.join(DEV_PROJECT_DIR, "templates", "dockerfile_ci")
# Subdirectories omitted when copying dev_project/ into CI build context.
CI_DEV_PROJECT_COPY_IGNORE_DIRS = frozenset(
    {"templates", "i18n", "__pycache__", ".git", "plugins"}
)
