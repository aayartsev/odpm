"""Sources change check / source plan (ADR-027)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project.config.payload import (
    compute_odoo_requirements_hash,
    hash_requirements_bytes,
    resolve_odoo_requirements_hash,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli import params as cli_params
from dev_project.image_layers.source_plan import (
    ODPM_FORCE_FULL_SOURCES,
    SourcePlanResult,
    analyze_source_plan,
    force_full_sources_requested,
    full_sources_result,
)
from dev_project.prepare.steps_git import (
    evaluate_git_materialize_dependencies,
    evaluate_git_materialize_platform,
)
from dev_project.prepare.sources_change_check import sources_change_check_eligible


class RequirementsHashTests(unittest.TestCase):
    def test_hash_bytes_matches_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.txt"
            data = b"decorator==5.2.1\n"
            path.write_bytes(data)
            self.assertEqual(
                hash_requirements_bytes(data),
                compute_odoo_requirements_hash(tmp),
            )

    def test_override_wins(self):
        config = MagicMock()
        config.odoo_requirements_hash_override = "abc"
        config.odoo_src_dir = ""
        config.docker_layout.docker_odoo_dir = ""
        self.assertEqual(resolve_odoo_requirements_hash(config), "abc")

    def test_host_tree_before_docker(self):
        with tempfile.TemporaryDirectory() as host, tempfile.TemporaryDirectory() as docker:
            Path(host, "requirements.txt").write_text("a\n", encoding="utf-8")
            Path(docker, "requirements.txt").write_text("b\n", encoding="utf-8")
            config = MagicMock()
            config.odoo_requirements_hash_override = None
            config.odoo_src_dir = host
            config.docker_layout.docker_odoo_dir = docker
            self.assertEqual(
                resolve_odoo_requirements_hash(config),
                compute_odoo_requirements_hash(host),
            )


class SourcePlanAnalyzeTests(unittest.TestCase):
    def _config(self):
        config = MagicMock()
        config.project_settings.odoo_version = "19.0"
        config.project_settings.odoo_build_date = "2026-01-01"
        config.project_settings.python_version = "3.12"
        config.project_settings.distro_name = "debian"
        config.project_settings.distro_version = "12"
        config.project_settings.arch = "amd64"
        config.project_settings.requirements_txt = []
        config.project_dir = "/tmp/proj"
        config.project_name = "demo"
        config.policy = MagicMock()
        config.policy.base_image_profile = "full"
        config.policy.venv_mode = "baked"
        config.compute_venv_lock_hash = MagicMock(return_value="lockhash")
        config.odoo_platform_project = MagicMock()
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = None
        return config

    def test_force_full_sources_env(self):
        with patch.dict(os.environ, {ODPM_FORCE_FULL_SOURCES: "1"}):
            self.assertTrue(force_full_sources_requested())
            result = analyze_source_plan(
                self._config(),
                program_dir=str(Path(__file__).resolve().parents[1]),
                remote=False,
            )
        self.assertTrue(result.full_sources)
        self.assertTrue(result.need_platform_tree)
        self.assertTrue(result.need_deps_trees)

    def test_platform_hit_skips_tree(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        cfg = self._config()

        def _presence(ref, *, remote, force=False):
            return "cache-platform-" in ref or "cache-venv-" in ref

        with (
            patch(
                "dev_project.image_layers.fingerprint._lock_sha_map",
                return_value={"platform": "abc"},
            ),
            patch(
                "dev_project.image_layers.source_plan.image_ref_exists",
                side_effect=_presence,
            ),
            patch(
                "dev_project.image_layers.source_plan._apply_requirements_hash_from_bare",
            ),
            patch(
                "dev_project.image_layers.source_plan.developing_git_sha_for_plan",
                return_value="deadbeef",
            ),
        ):
            result = analyze_source_plan(
                cfg,
                program_dir=program_dir,
                remote=False,
                ensure_bare=lambda: "/tmp/mirror.git",
            )
        self.assertTrue(result.sources_change_check_active)
        self.assertFalse(result.need_platform_tree)
        self.assertTrue(result.platform_hit)
        self.assertTrue(result.venv_hit)
        self.assertFalse(result.need_deps_trees)

    def test_fail_soft_on_presence_error(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        with (
            patch(
                "dev_project.image_layers.fingerprint._lock_sha_map",
                return_value={"platform": "abc"},
            ),
            patch(
                "dev_project.image_layers.source_plan.image_ref_exists",
                side_effect=RuntimeError("no crane"),
            ),
            patch(
                "dev_project.image_layers.source_plan._apply_requirements_hash_from_bare",
            ),
        ):
            result = analyze_source_plan(
                self._config(),
                program_dir=program_dir,
                remote=True,
                ensure_bare=lambda: "/tmp/mirror.git",
            )
        self.assertTrue(result.fail_soft)
        self.assertTrue(result.full_sources)
        self.assertTrue(result.need_platform_tree)


class SourcesChangeCheckEligibleTests(unittest.TestCase):
    def test_ci_stop_after_sources(self):
        ctx = MagicMock()
        ctx.host_ctx.policy.is_ci.return_value = True
        ctx.args = OdpmCliArgs(stop_after=cli_params.STOP_AFTER_SOURCES)
        with patch.dict(os.environ, {ODPM_FORCE_FULL_SOURCES: ""}, clear=False):
            os.environ.pop(ODPM_FORCE_FULL_SOURCES, None)
            self.assertTrue(sources_change_check_eligible(ctx))

    def test_non_ci(self):
        ctx = MagicMock()
        ctx.host_ctx.policy.is_ci.return_value = False
        ctx.args = OdpmCliArgs(stop_after=cli_params.STOP_AFTER_SOURCES)
        self.assertFalse(sources_change_check_eligible(ctx))


class SourcesChangeCheckEvaluateTests(unittest.TestCase):
    def test_materialize_platform_noop_on_hit(self):
        ctx = MagicMock()
        ctx.host_ctx.policy.is_ci.return_value = True
        ctx.args = OdpmCliArgs(stop_after=cli_params.STOP_AFTER_SOURCES)
        ctx.host_ctx.arguments = ctx.args
        ctx.source_plan = SourcePlanResult(
            sources_change_check_active=True,
            full_sources=False,
            need_platform_tree=False,
            need_platform_bare=True,
            need_deps_trees=False,
            platform_hit=True,
            venv_hit=True,
            deps_hit=None,
            app_hit=False,
            lint_hit=None,
            reason="test",
        )
        with (
            patch("dev_project.prepare.steps_git.skip_git", return_value=False),
            patch("dev_project.prepare.steps_git.update_lock", return_value=False),
            patch(
                "dev_project.prepare.sources_change_check.sources_change_check_eligible",
                return_value=True,
            ),
            patch(
                "dev_project.prepare.sources_change_check.get_or_build_source_plan",
                return_value=ctx.source_plan,
            ),
        ):
            step = evaluate_git_materialize_platform(ctx)
            deps = evaluate_git_materialize_dependencies(ctx)
        self.assertEqual(step.outcome, "noop")
        self.assertFalse(step.should_execute())
        self.assertEqual(deps.outcome, "noop")


class FullSourcesHelperTests(unittest.TestCase):
    def test_full_sources_result_flags(self):
        result = full_sources_result(reason="x", fail_soft=True)
        self.assertTrue(result.full_sources)
        self.assertTrue(result.fail_soft)
        self.assertTrue(result.need_platform_tree)


if __name__ == "__main__":
    unittest.main()
