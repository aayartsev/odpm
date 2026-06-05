import os

from .paths import DEV_PROJECT_DIR, PROJECT_SERVICE_DIRECTORY

CI_BUILD_CONTEXT_DIR = os.path.join(PROJECT_SERVICE_DIRECTORY, "ci-build-context")
CI_BAKE_DIR = "bake"
CI_VENV_INSTALL_JSON = "venv_install.json"
CI_BAKE_ENTRYPOINT = "bake.inside_docker_app.main"
DEV_ENTRYPOINT = "dev_project.inside_docker_app.main"
CI_BAKE_PYTHON_FILES = (
    "constants/__init__.py",
    "constants/paths.py",
    "constants/scenarios.py",
    "constants/core.py",
    "constants/ci.py",
    "bake_venv.py",
    os.path.join("inside_docker_app", "main.py"),
    os.path.join("inside_docker_app", "container_bootstrap.py"),
    os.path.join("inside_docker_app", "check_odoo.py"),
    os.path.join("inside_docker_app", "check_virtualenv.py"),
    os.path.join("inside_docker_app", "postgres_waiter.py"),
    os.path.join("inside_docker_app", "utils.py"),
    os.path.join("inside_docker_app", "logger.py"),
    os.path.join("inside_docker_app", "parse_args.py"),
    os.path.join("inside_docker_app", "cli_params.py"),
)
CI_DOCKERFILE = "Dockerfile.ci"
CI_DOCKERFILE_TEMPLATE = os.path.join(DEV_PROJECT_DIR, "templates", "dockerfile_ci")
