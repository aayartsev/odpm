"""Opt-in docker build integration for the CI image bake path."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from dev_project import constants
from dev_project.translations import _
from tests.ci_build_context import (
    DEFAULT_DOCKER_PROJECT_DIR,
    write_minimal_ci_build_context,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKERFILE_CI_TEMPLATE = (
    PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_ci"
)

RUN_DOCKER_INTEGRATION = os.environ.get("ODPM_RUN_DOCKER_INTEGRATION") == "1"
BASE_IMAGE_TAG = "odpm-ci-integration-base:test"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _build_base_image() -> None:
    dockerfile = "\n".join(
        [
            "FROM python:3.12-slim",
            "RUN groupadd -g 9999 odoo && "
            "useradd -u 9999 -g odoo -m -s /bin/bash odoo",
        ]
    )
    with tempfile.NamedTemporaryFile("w", suffix=".Dockerfile", delete=False) as handle:
        handle.write(dockerfile)
        dockerfile_path = handle.name
    try:
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                dockerfile_path,
                "-t",
                BASE_IMAGE_TAG,
                ".",
            ],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
        )
    finally:
        os.unlink(dockerfile_path)


def _write_ci_dockerfile(context_dir: Path, *, base_image: str) -> Path:
    content = DOCKERFILE_CI_TEMPLATE.read_text(encoding="utf-8")
    content = content.format(
        BASE_IMAGE=base_image,
        DOCKER_PROJECT_DIR=DEFAULT_DOCKER_PROJECT_DIR,
        CONTAINER_USER=constants.CONTAINER_USER,
        CURRENT_USER=constants.CONTAINER_USER,
        CI_VENV_INSTALL_JSON=constants.CI_VENV_INSTALL_JSON,
        CI_RUNTIME_CONFIG_CONTEXT_REL=constants.CI_RUNTIME_CONFIG_CONTEXT_REL_PATH,
        ODPM_CONFIG_PATH_ENV=constants.ODPM_CONFIG_PATH_ENV,
        ODPM_RUNTIME_CONFIG_CONTAINER_PATH=constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH,
        CI_SECRETS_DOCKERFILE_BLOCK="",
    )
    content = content.replace(
        constants.MESSAGE_MARKER,
        _('Do not change this file, its content is generating automatically'),
    )
    dockerfile_path = context_dir / constants.CI_DOCKERFILE
    dockerfile_path.write_text(content, encoding="utf-8")
    return dockerfile_path


@unittest.skipUnless(RUN_DOCKER_INTEGRATION, "set ODPM_RUN_DOCKER_INTEGRATION=1")
@unittest.skipUnless(_docker_available(), "docker not available")
class CiImageBuildIntegrationTests(unittest.TestCase):
    _base_image_built = False

    @classmethod
    def setUpClass(cls) -> None:
        if not cls._base_image_built:
            _build_base_image()
            cls._base_image_built = True

    def setUp(self) -> None:
        self._image_tag = f"odpm-ci-integration:{uuid.uuid4().hex[:12]}"

    def tearDown(self) -> None:
        subprocess.run(
            ["docker", "rmi", "-f", self._image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_docker_build_produces_ci_image(self):
        with tempfile.TemporaryDirectory() as context_dir:
            write_minimal_ci_build_context(
                context_dir,
                docker_project_dir=DEFAULT_DOCKER_PROJECT_DIR,
                lock_hash="ci-image-build-integration",
            )
            dockerfile_path = _write_ci_dockerfile(
                Path(context_dir),
                base_image=BASE_IMAGE_TAG,
            )
            subprocess.run(
                [
                    "docker",
                    "build",
                    "-f",
                    str(dockerfile_path),
                    "-t",
                    self._image_tag,
                    context_dir,
                ],
                check=True,
                text=True,
            )
            inspect = subprocess.run(
                ["docker", "image", "inspect", self._image_tag],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(self._image_tag, inspect.stdout)


if __name__ == "__main__":
    unittest.main()
