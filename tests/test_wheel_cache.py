"""Unit tests for shared wheel cache helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from dev_project import constants
from dev_project.wheel_cache import (
    apply_wheel_cache_env,
    host_cache_mounts,
    resolve_cache_root,
    resolve_wheel_cache_env,
)


class ResolveCacheRootTests(unittest.TestCase):
    def test_default_under_home_odpm(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(constants.ODPM_WHEEL_CACHE_ROOT_ENV, None)
            root = resolve_cache_root({})
        self.assertEqual(
            root,
            os.path.join(
                os.path.expanduser("~"),
                constants.CONFIG_DIR_IN_HOME_DIR,
                constants.DEFAULT_WHEEL_CACHE_DIRNAME,
            ),
        )

    def test_custom_root_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = resolve_cache_root(
                {constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp}
            )
            self.assertEqual(root, os.path.abspath(tmp))


class ResolveWheelCacheEnvTests(unittest.TestCase):
    def test_default_paths_for_python_312(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp}
            with patch(
                "dev_project.wheel_cache.use_container_cache_layout",
                return_value=False,
            ):
                resolved = resolve_wheel_cache_env(
                    python_version="3.12", env=env
                )
            self.assertEqual(
                resolved[constants.PIP_CACHE_DIR_ENV],
                os.path.join(tmp, "wheels", "3.12"),
            )
            self.assertEqual(
                resolved[constants.UV_CACHE_DIR_ENV],
                os.path.join(tmp, "uv"),
            )
            self.assertTrue(os.path.isdir(resolved[constants.PIP_CACHE_DIR_ENV]))
            self.assertTrue(os.path.isdir(resolved[constants.UV_CACHE_DIR_ENV]))

    def test_respects_existing_pip_and_uv_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp,
                constants.PIP_CACHE_DIR_ENV: "/explicit/pip",
                constants.UV_CACHE_DIR_ENV: "/explicit/uv",
            }
            with patch(
                "dev_project.wheel_cache.use_container_cache_layout",
                return_value=False,
            ):
                resolved = resolve_wheel_cache_env(
                    python_version="3.12", env=env, mkdir=False
                )
            self.assertEqual(resolved, {})

    def test_container_layout_uses_fixed_paths(self):
        with patch(
            "dev_project.wheel_cache.use_container_cache_layout",
            return_value=True,
        ):
            with patch("os.makedirs"):
                resolved = resolve_wheel_cache_env(
                    python_version="3.11", env={}, mkdir=True
                )
        self.assertEqual(
            resolved[constants.PIP_CACHE_DIR_ENV],
            "/cache/odpm/wheels/3.11",
        )
        self.assertEqual(
            resolved[constants.UV_CACHE_DIR_ENV],
            "/cache/odpm/uv",
        )


class ApplyWheelCacheEnvTests(unittest.TestCase):
    def test_apply_merges_into_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = {constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp}
            with patch(
                "dev_project.wheel_cache.use_container_cache_layout",
                return_value=False,
            ):
                applied = apply_wheel_cache_env(
                    python_version="3.12", env=target
                )
            self.assertIn(constants.PIP_CACHE_DIR_ENV, target)
            self.assertEqual(applied[constants.PIP_CACHE_DIR_ENV], target[constants.PIP_CACHE_DIR_ENV])


class HostCacheMountsTests(unittest.TestCase):
    def test_mounts_uv_and_pip_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            mounts = host_cache_mounts(python_version="3.12", cache_root=tmp)
            self.assertEqual(len(mounts), 2)
            self.assertEqual(mounts[0].local, os.path.join(tmp, "uv"))
            self.assertEqual(mounts[0].docker, "/cache/odpm/uv")
            self.assertEqual(mounts[1].local, os.path.join(tmp, "wheels", "3.12"))
            self.assertEqual(mounts[1].docker, "/cache/odpm/wheels/3.12")

    def test_mounts_respect_env_wheel_cache_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            mounts = host_cache_mounts(
                python_version="3.12",
                env={constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp},
            )
            self.assertTrue(mounts[0].local.startswith(tmp))
            self.assertEqual(
                mounts[1].local, os.path.join(tmp, "wheels", "3.12")
            )


if __name__ == "__main__":
    unittest.main()
