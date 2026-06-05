import os

from .paths import DEV_PROJECT_DIR, PROJECT_SERVICE_DIRECTORY

CI_BUILD_CONTEXT_DIR = os.path.join(PROJECT_SERVICE_DIRECTORY, "ci-build-context")
CI_VENV_SPEC_DIR = "ci"
CI_VENV_INSTALL_JSON = os.path.join(CI_VENV_SPEC_DIR, "venv_install.json")
DEV_ENTRYPOINT = "dev_project.inside_docker_app.main"
CI_DOCKERFILE = "Dockerfile.ci"
CI_DOCKERFILE_TEMPLATE = os.path.join(DEV_PROJECT_DIR, "templates", "dockerfile_ci")
