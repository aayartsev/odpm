"""Unit tests for CI image build backends (ADR-016)."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import PipelineError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.project_env.image_build import (
    ImageBuildSpec,
    get_ci_image_build_backend,
    resolve_ci_image_builder,
    resolve_ci_image_push,
)
from dev_project.project_env.image_build.docker_backend import DockerImageBuildBackend
from dev_project.project_env.image_build.kaniko_backend import KanikoImageBuildBackend


def _spec(**kwargs) -> ImageBuildSpec:
    base = dict(
        context_dir="/tmp/ctx",
        dockerfile="/tmp/ctx/Dockerfile.ci",
        tag="registry/app:19",
        platform="linux/amd64",
        push=False,
        project_dir="/tmp/project",
    )
    base.update(kwargs)
    return ImageBuildSpec(**base)


class ResolveCiImageBuilderTests(unittest.TestCase):
    def test_default_is_docker(self):
        self.assertEqual(resolve_ci_image_builder(None, environ={}), "docker")

    def test_cli_overrides_env(self):
        args = OdpmCliArgs(image_builder="docker")
        self.assertEqual(
            resolve_ci_image_builder(
                args,
                environ={constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko"},
            ),
            "docker",
        )

    def test_env_when_cli_unset(self):
        self.assertEqual(
            resolve_ci_image_builder(
                OdpmCliArgs(),
                environ={constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko"},
            ),
            "kaniko",
        )

    def test_dotenv_dict_without_process_env(self):
        """Layered dotenv mapping must drive resolve when passed explicitly."""
        from dev_project.system_check_policy import merged_environ_for_resolve

        dotenv = {constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko"}
        environ = merged_environ_for_resolve(dotenv, process_environ={})
        self.assertEqual(
            resolve_ci_image_builder(OdpmCliArgs(), environ=environ),
            "kaniko",
        )

    def test_unknown_builder_raises(self):
        with self.assertRaises(PipelineError) as ctx:
            resolve_ci_image_builder(
                None,
                environ={constants.ODPM_CI_IMAGE_BUILDER_ENV: "buildah"},
            )
        self.assertIn("buildah", str(ctx.exception))


class ResolveCiImagePushTests(unittest.TestCase):
    def test_default_false(self):
        self.assertFalse(resolve_ci_image_push(OdpmCliArgs(), environ={}))

    def test_cli_true(self):
        self.assertTrue(resolve_ci_image_push(OdpmCliArgs(image_push=True), environ={}))

    def test_env_truthy(self):
        for value in ("1", "true", "YES"):
            with self.subTest(value=value):
                self.assertTrue(
                    resolve_ci_image_push(
                        OdpmCliArgs(),
                        environ={constants.ODPM_CI_IMAGE_PUSH_ENV: value},
                    )
                )


class DockerImageBuildBackendTests(unittest.TestCase):
    def test_build_argv(self):
        argv = DockerImageBuildBackend().build_argv(_spec())
        self.assertEqual(
            argv,
            [
                "docker",
                "build",
                "-f",
                "/tmp/ctx/Dockerfile.ci",
                "-t",
                "registry/app:19",
                "--platform=linux/amd64",
                "/tmp/ctx",
            ],
        )

    @patch("dev_project.project_env.image_build.docker_backend.run_logged")
    def test_build_pushes_when_requested(self, mock_run):
        mock_run.return_value = 0
        DockerImageBuildBackend().build(_spec(push=True))
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(
            mock_run.call_args_list[1].args[0],
            ["docker", "push", "registry/app:19"],
        )

    @patch("dev_project.project_env.image_build.docker_backend.run_logged")
    def test_build_failure_raises(self, mock_run):
        mock_run.return_value = 7
        with self.assertRaises(PipelineError) as ctx:
            DockerImageBuildBackend().build(_spec())
        self.assertEqual(ctx.exception.exit_code, 7)


class KanikoImageBuildBackendTests(unittest.TestCase):
    def test_docker_run_no_push_argv(self):
        backend = KanikoImageBuildBackend(environ={}, home_dir="/home/ci")
        argv = backend.build_argv(_spec())
        self.assertEqual(argv[0:4], ["docker", "run", "--rm", "-v"])
        self.assertIn("/tmp/ctx:/workspace", argv)
        self.assertIn(constants.DEFAULT_KANIKO_EXECUTOR_IMAGE, argv)
        self.assertIn("--no-push", argv)
        self.assertIn(
            f"--tar-path=/workspace/{constants.CI_IMAGE_TAR_NAME}",
            argv,
        )
        self.assertNotIn("--destination=registry/app:19", argv)

    def test_docker_run_push_mounts_docker_config(self):
        with tempfile.TemporaryDirectory() as home:
            docker_dir = Path(home) / ".docker"
            docker_dir.mkdir()
            config = docker_dir / "config.json"
            config.write_text("{}", encoding="utf-8")
            backend = KanikoImageBuildBackend(environ={}, home_dir=home)
            argv = backend.build_argv(_spec(push=True))
            self.assertIn(f"{config}:/kaniko/.docker/config.json:ro", argv)
            self.assertIn("--destination=registry/app:19", argv)
            self.assertNotIn("--no-push", argv)

    def test_docker_run_push_without_docker_config_raises(self):
        with tempfile.TemporaryDirectory() as home:
            backend = KanikoImageBuildBackend(environ={}, home_dir=home)
            with self.assertRaises(PipelineError) as ctx:
                backend.build_argv(_spec(push=True))
            self.assertIn("config.json", str(ctx.exception))

    def test_direct_mode_argv(self):
        backend = KanikoImageBuildBackend(
            environ={
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
                constants.ODPM_KANIKO_EXECUTOR_BIN_ENV: "/usr/local/bin/executor",
            }
        )
        argv = backend.build_argv(_spec(push=True))
        self.assertEqual(
            argv,
            [
                "/usr/local/bin/executor",
                "--dockerfile=/tmp/ctx/Dockerfile.ci",
                "--context=dir:///tmp/ctx",
                "--custom-platform=linux/amd64",
                "--destination=registry/app:19",
            ],
        )

    def test_direct_mode_argv_with_wrapper_and_extra_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = Path(tmp) / "run-kaniko.sh"
            wrapper.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
            wrapper.chmod(0o755)
            backend = KanikoImageBuildBackend(
                environ={
                    constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
                    constants.ODPM_KANIKO_EXECUTOR_BIN_ENV: "/usr/local/bin/executor",
                    constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV: str(wrapper),
                    constants.ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS_ENV: (
                        "--kaniko-dir=/tmp/kaniko"
                    ),
                }
            )
            argv = backend.build_argv(_spec(push=True))
            self.assertEqual(
                argv[:4],
                [
                    str(wrapper),
                    "/usr/local/bin/executor",
                    "--kaniko-dir=/tmp/kaniko",
                    "--dockerfile=/tmp/ctx/Dockerfile.ci",
                ],
            )

    @patch.object(os, "geteuid", return_value=1000, create=True)
    def test_direct_mode_argv_with_sudo_opt_in(self, _mock_geteuid):
        backend = KanikoImageBuildBackend(
            environ={
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
                constants.ODPM_KANIKO_EXECUTOR_BIN_ENV: "/usr/local/bin/executor",
                constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV: "1",
            }
        )
        argv = backend.build_argv(_spec(push=True))
        self.assertEqual(
            argv[:3],
            ["sudo", "-n", "/usr/local/bin/executor"],
        )

    @patch.object(os, "geteuid", return_value=1000, create=True)
    def test_direct_wrapper_takes_precedence_over_sudo(self, _mock_geteuid):
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = Path(tmp) / "run-kaniko.sh"
            wrapper.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
            wrapper.chmod(0o755)
            backend = KanikoImageBuildBackend(
                environ={
                    constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
                    constants.ODPM_KANIKO_EXECUTOR_BIN_ENV: "/usr/local/bin/executor",
                    constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV: str(wrapper),
                    constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV: "1",
                }
            )
            argv = backend.build_argv(_spec())
            self.assertEqual(argv[0], str(wrapper))
            self.assertNotIn("sudo", argv)

    @patch.object(os, "geteuid", return_value=1000, create=True)
    def test_validate_direct_launch_requires_wrapper_or_sudo(self, _mock_geteuid):
        backend = KanikoImageBuildBackend(
            environ={
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
            }
        )
        with self.assertRaises(PipelineError) as ctx:
            backend.validate_direct_launch()
        message = str(ctx.exception)
        self.assertIn(constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV, message)
        self.assertIn(constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV, message)

    @patch.object(os, "geteuid", return_value=1000, create=True)
    def test_build_direct_without_privilege_launch_raises_before_executor(
        self, _mock_geteuid
    ):
        backend = KanikoImageBuildBackend(
            environ={
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
            }
        )
        with self.assertRaises(PipelineError):
            backend.build(_spec())

    @patch("dev_project.project_env.image_build.kaniko_backend.subprocess.run")
    @patch.object(os, "geteuid", return_value=1000, create=True)
    def test_validate_direct_sudo_requires_passwordless(
        self, _mock_geteuid, mock_run
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["sudo", "-n", "true"],
            returncode=1,
            stdout="",
            stderr="",
        )
        backend = KanikoImageBuildBackend(
            environ={
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
                constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV: "true",
            }
        )
        with self.assertRaises(PipelineError) as ctx:
            backend.validate_direct_launch()
        self.assertIn("passwordless sudo", str(ctx.exception))

    def test_unknown_mode_raises(self):
        backend = KanikoImageBuildBackend(
            environ={constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "pod"}
        )
        with self.assertRaises(PipelineError):
            backend.build_argv(_spec())

    @patch("dev_project.project_env.image_build.kaniko_backend.run_logged")
    def test_build_failure_raises(self, mock_run):
        mock_run.return_value = 3
        with self.assertRaises(PipelineError) as ctx:
            KanikoImageBuildBackend(environ={}).build(_spec())
        self.assertEqual(ctx.exception.exit_code, 3)


class FactoryAndCiImageWireTests(unittest.TestCase):
    def test_factory_returns_backends(self):
        self.assertIsInstance(
            get_ci_image_build_backend("docker"),
            DockerImageBuildBackend,
        )
        self.assertIsInstance(
            get_ci_image_build_backend("kaniko"),
            KanikoImageBuildBackend,
        )

    def test_factory_unknown_raises(self):
        with self.assertRaises(PipelineError):
            get_ci_image_build_backend("buildah")

    @patch("dev_project.project_env.ci_image.get_ci_image_build_backend")
    @patch("dev_project.project_env.ci_image.BaseImageService")
    @patch("dev_project.project_env.ci_image.BaseImageBuilder")
    def test_ci_image_builder_uses_docker_backend_and_ensures_base(
        self, mock_base_builder_cls, mock_base_svc, mock_get_backend
    ):
        from dev_project.project_env.ci_image import CiImageBuilder

        backend = MagicMock()
        mock_get_backend.return_value = backend
        mock_base_builder_cls.return_value.resolve_base_image_ref.return_value = (
            "base:tag"
        )
        env = MagicMock()
        config = MagicMock()
        config.arguments = OdpmCliArgs(image_builder="docker", image_push=False)
        config.odoo_ci_image_name = "ci:tag"
        config.odoo_image_name = "base:tag"
        config.ci_build_context_dir = "/tmp/ctx"
        config.arch = "amd64"
        config.project_dir = "/tmp/project"
        config.program_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        config.user_env = MagicMock()
        config.user_env.project_dotenv_dict.return_value = {}
        env.config = config
        builder = CiImageBuilder(env)
        builder.prepare_ci_build_context = MagicMock()
        builder.generate_ci_dockerfile = MagicMock(return_value="/tmp/ctx/Dockerfile.ci")

        builder.build_ci_image()

        mock_base_svc.return_value.ensure_base_image.assert_called_once()
        mock_get_backend.assert_called_once_with("docker")
        backend.build.assert_called_once()
        spec = backend.build.call_args.args[0]
        self.assertEqual(spec.tag, "ci:tag")
        self.assertFalse(spec.push)

    @patch("dev_project.project_env.ci_image.get_ci_image_build_backend")
    @patch("dev_project.project_env.ci_image.BaseImageService")
    @patch("dev_project.project_env.ci_image.BaseImageBuilder")
    def test_ci_image_builder_kaniko_ensures_base(
        self, mock_base_builder_cls, mock_base_svc, mock_get_backend
    ):
        from dev_project.project_env.ci_image import CiImageBuilder

        backend = MagicMock()
        mock_get_backend.return_value = backend
        mock_base_builder_cls.return_value.resolve_base_image_ref.return_value = (
            "registry.example.com/odpm/base:latest"
        )
        env = MagicMock()
        config = MagicMock()
        config.arguments = OdpmCliArgs(image_builder="kaniko", image_push=True)
        config.odoo_ci_image_name = "registry/app:1"
        config.odoo_image_name = "registry/base:1"
        config.ci_build_context_dir = "/tmp/ctx"
        config.arch = "arm64"
        config.project_dir = "/tmp/project"
        config.user_env = MagicMock()
        config.user_env.project_dotenv_dict.return_value = {
            constants.ODPM_BASE_IMAGE_REGISTRY_ENV: "registry.example.com/odpm",
            constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko",
        }
        env.config = config
        builder = CiImageBuilder(env)
        builder.prepare_ci_build_context = MagicMock()
        builder.generate_ci_dockerfile = MagicMock(return_value="/tmp/ctx/Dockerfile.ci")

        builder.build_ci_image()

        mock_base_svc.return_value.ensure_base_image.assert_called_once()
        mock_get_backend.assert_called_once_with("kaniko")
        spec = backend.build.call_args.args[0]
        self.assertTrue(spec.push)
        self.assertEqual(spec.platform, "linux/arm64")


class CliImageBuilderFlagTests(unittest.TestCase):
    def test_parse_image_builder_and_push(self):
        from dev_project.host.cli.parse_args import parse_cli_args

        args = parse_cli_args(
            ["--build-image", "--image-builder", "kaniko", "--image-push"]
        )
        self.assertTrue(args.build_image)
        self.assertEqual(args.image_builder, "kaniko")
        self.assertTrue(args.image_push)


if __name__ == "__main__":
    unittest.main()
