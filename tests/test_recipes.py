"""Tests for odpm recipes framework."""

from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.plan.cli import is_run_mode
from dev_project.recipes.builtin.apply_modules_from_diff import ApplyModulesFromDiffRecipe
from dev_project.recipes.builtin.pull_remote_db import PullRemoteDbRecipe
from dev_project.recipes.invoke import RECIPE_DEPTH_ENV, guard_step_argv
from dev_project.recipes.registry import get_recipe, list_recipes
from dev_project.recipes.runner import resolve_params, run_recipe
from dev_project.recipes.types import OdpmStep, RecipeContext, StepResult
from dev_project.recipes.yaml_loader import parse_recipe_yaml, substitute_argv
from dev_project.recipes.yaml_recipe import yaml_recipe_from_raw
from dev_project.system_check_policy import cli_allows_ci_explicit_mode


class YamlSubstTests(unittest.TestCase):
    def test_param_and_env_subst(self):
        argv = substitute_argv(
            ["-d", "${param.database}", "--x", "${env:FOO}"],
            params={"database": "prod"},
            environ={"FOO": "bar"},
        )
        self.assertEqual(argv, ["-d", "prod", "--x", "bar"])

    def test_missing_param_raises(self):
        with self.assertRaises(ConfigError):
            substitute_argv(
                ["${param.missing}"],
                params={},
                environ={},
            )

    def test_yaml_load_and_recipe(self):
        raw = parse_recipe_yaml(
            """
name: example-backup
description: Backup then skip-start
params:
  database:
    required: true
    env: ODPM_RUN_DATABASE
steps:
  - odpm: ["-d", "${param.database}", "--db-backup"]
  - odpm: ["--skip-start"]
"""
        )
        recipe = yaml_recipe_from_raw(raw, source="<test>")
        params = resolve_params(
            recipe,
            cli_values={"database": "db1"},
            environ={},
        )
        ctx = RecipeContext(
            project_dir="/tmp",
            program_dir="/tmp",
            params=params,
            environ={},
        )
        recipe.reset(ctx)
        first = recipe.next_step(ctx)
        assert first is not None
        self.assertEqual(list(first.argv), ["-d", "db1", "--db-backup"])
        second = recipe.next_step(ctx)
        assert second is not None
        self.assertEqual(list(second.argv), ["--skip-start"])
        self.assertIsNone(recipe.next_step(ctx))

    def test_missing_required_param(self):
        raw = parse_recipe_yaml(
            """
name: need-db
params:
  database:
    required: true
    env: ODPM_RUN_DATABASE
steps:
  - odpm: ["-d", "${param.database}"]
"""
        )
        recipe = yaml_recipe_from_raw(raw, source="<test>")
        with self.assertRaises(ConfigError):
            resolve_params(recipe, cli_values={}, environ={})


class ApplyModulesFromDiffTests(unittest.TestCase):
    def test_plan_omits_empty_flags_and_records(self):
        recipe = ApplyModulesFromDiffRecipe()
        ctx = RecipeContext(
            project_dir="/tmp/p",
            program_dir="/tmp",
            params={"database": "prod"},
            environ={},
        )
        recipe.reset(ctx)
        diff_step = recipe.next_step(ctx)
        assert diff_step is not None
        self.assertTrue(diff_step.capture)
        self.assertTrue(diff_step.execute_even_if_dry_run)
        ctx.step_results.append(
            StepResult(
                returncode=0,
                stdout=json.dumps(
                    {"init_modules": "a", "update_modules": "", "base": "b", "head": "h"}
                ),
            )
        )
        apply_step = recipe.next_step(ctx)
        assert apply_step is not None
        self.assertEqual(
            list(apply_step.argv),
            ["-d", "prod", "-i", "a", "--odoo-bin", "--stop-after-init"],
        )
        self.assertIsNone(apply_step.timeout)
        record = recipe.next_step(ctx)
        assert record is not None
        self.assertEqual(list(record.argv), ["modules", "record-applied"])
        self.assertIsNone(recipe.next_step(ctx))

    def test_both_empty_skips_apply_still_records(self):
        recipe = ApplyModulesFromDiffRecipe()
        ctx = RecipeContext(
            project_dir="/tmp/p",
            program_dir="/tmp",
            params={"database": "prod"},
            environ={},
        )
        recipe.reset(ctx)
        recipe.next_step(ctx)
        ctx.step_results.append(
            StepResult(
                returncode=0,
                stdout=json.dumps(
                    {"init_modules": "", "update_modules": "", "base": "b", "head": "h"}
                ),
            )
        )
        record = recipe.next_step(ctx)
        assert record is not None
        self.assertEqual(list(record.argv), ["modules", "record-applied"])


class RunnerTests(unittest.TestCase):
    def test_dry_run_prints_and_executes_capture_steps_only(self):
        recipe = ApplyModulesFromDiffRecipe()
        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(list(argv))
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps(
                {"init_modules": "m1", "update_modules": "m2", "base": "b", "head": "h"}
            )
            result.stderr = ""
            return result

        with tempfile.TemporaryDirectory() as tmp:
            with patch("dev_project.recipes.runner.subprocess.run", side_effect=fake_run):
                buf = StringIO()
                with patch("sys.stdout", buf):
                    code = run_recipe(
                        recipe,
                        project_dir=tmp,
                        program_dir=tmp,
                        params={"database": "db"},
                        environ={},
                        dry_run=True,
                    )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertIn("modules", calls[0])
            self.assertIn("diff", calls[0])
            printed = buf.getvalue()
            self.assertIn("modules", printed)
            self.assertIn("record-applied", printed)
            self.assertIn("-i", printed)
            self.assertIn("m1", printed)

    def test_fail_fast(self):
        class TwoStep:
            name = "two"
            description = ""

            def params(self):
                return ()

            def reset(self, ctx):
                self._i = 0

            def next_step(self, ctx):
                if self._i == 0:
                    self._i = 1
                    return OdpmStep(argv=("modules", "diff", "--format", "json"), capture=True)
                if self._i == 1:
                    self._i = 2
                    return OdpmStep(argv=("modules", "record-applied"))
                return None

        def fake_run(argv, **kwargs):
            result = MagicMock()
            result.returncode = 7
            result.stdout = ""
            result.stderr = "boom"
            return result

        with tempfile.TemporaryDirectory() as tmp:
            with patch("dev_project.recipes.runner.subprocess.run", side_effect=fake_run):
                with self.assertRaises(ConfigError) as ctx:
                    run_recipe(
                        TwoStep(),
                        project_dir=tmp,
                        program_dir=tmp,
                        params={},
                        environ={},
                        dry_run=False,
                    )
            self.assertEqual(ctx.exception.exit_code, 7)

    def test_guard_forbids_run_token(self):
        with self.assertRaises(ConfigError):
            guard_step_argv(["run", "x"])

    def test_nested_run_forbidden_by_depth(self):
        recipe = ApplyModulesFromDiffRecipe()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                run_recipe(
                    recipe,
                    project_dir=tmp,
                    program_dir=tmp,
                    params={"database": "db"},
                    environ={RECIPE_DEPTH_ENV: "1"},
                    dry_run=True,
                )


class PullRemoteDbRecipeTests(unittest.TestCase):
    def test_phases_timeout_none_and_no_secret_in_argv(self):
        recipe = PullRemoteDbRecipe()
        ctx = RecipeContext(
            project_dir="/tmp/p",
            program_dir="/tmp",
            params={
                "database": "local",
                "url": "https://client.example.com",
                "remote_db": "prod",
            },
            environ={},
        )
        recipe.reset(ctx)
        pull = recipe.next_step(ctx)
        assert pull is not None
        self.assertEqual(
            list(pull.argv),
            [
                "database",
                "pull",
                "--url",
                "https://client.example.com",
                "--remote-db",
                "prod",
            ],
        )
        self.assertTrue(pull.capture)
        self.assertFalse(pull.execute_even_if_dry_run)
        self.assertIsNone(pull.timeout)
        self.assertNotIn("master", " ".join(pull.argv).lower())
        self.assertNotIn("pwd", " ".join(pull.argv).lower())
        ctx.step_results.append(
            StepResult(returncode=0, stdout="host_prod_2026.zip\n")
        )
        restore = recipe.next_step(ctx)
        assert restore is not None
        self.assertEqual(
            list(restore.argv),
            ["-d", "local", "--db-restore", "host_prod_2026.zip"],
        )
        self.assertIsNone(restore.timeout)
        self.assertFalse(restore.execute_even_if_dry_run)
        self.assertIsNone(recipe.next_step(ctx))

    def test_dry_run_skips_network_and_prints_plan(self):
        recipe = get_recipe("pull-remote-db")
        executed: list[list[str]] = []

        def fake_run(argv, **kwargs):
            executed.append(list(argv))
            return MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            with patch("dev_project.recipes.runner.subprocess.run", side_effect=fake_run):
                with patch("sys.stdout", new_callable=StringIO) as out:
                    code = run_recipe(
                        recipe,
                        project_dir=tmp,
                        program_dir=tmp,
                        params={
                            "database": "local",
                            "url": "https://client.example.com",
                            "remote_db": "prod",
                        },
                        dry_run=True,
                    )
        self.assertEqual(code, 0)
        self.assertEqual(executed, [])
        plan = out.getvalue()
        self.assertIn("database pull", plan)
        self.assertIn("--db-restore", plan)
        self.assertIn("<archive.zip>", plan)


class CliAndAllowlistTests(unittest.TestCase):
    def test_parse_run_list(self):
        args = parse_cli_args(["run", "--list"])
        self.assertEqual(args.command, "run")
        self.assertTrue(args.run_list)
        self.assertTrue(is_run_mode(args))

    def test_parse_run_recipe_dry_run(self):
        args = parse_cli_args(
            ["run", "apply-modules-from-diff", "--dry-run", "-d", "db", "--diff-base", "abc"]
        )
        self.assertEqual(args.run_recipe, "apply-modules-from-diff")
        self.assertTrue(args.run_dry_run)
        self.assertEqual(args.d, "db")
        self.assertEqual(args.run_diff_base, "abc")

    def test_parse_run_pull_remote_flags(self):
        args = parse_cli_args(
            [
                "run",
                "pull-remote-db",
                "-d",
                "local",
                "--url",
                "https://client.example.com",
                "--remote-db",
                "prod",
            ]
        )
        self.assertEqual(args.run_recipe, "pull-remote-db")
        self.assertEqual(args.run_remote_url, "https://client.example.com")
        self.assertEqual(args.run_remote_db, "prod")
        self.assertEqual(args.d, "local")

    def test_ci_allowlist_run(self):
        self.assertTrue(cli_allows_ci_explicit_mode(OdpmCliArgs(command="run")))
        self.assertTrue(cli_allows_ci_explicit_mode(OdpmCliArgs(run_list=True)))
        # Child apply path remains disallowed in ci (documented policy).
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs(d="db", i="sale")))

    def test_builtin_listed(self):
        names = [r.name for r in list_recipes(project_dir=None)]
        self.assertIn("apply-modules-from-diff", names)
        self.assertIn("pull-remote-db", names)
        recipe = get_recipe("pull-remote-db")
        self.assertEqual(recipe.name, "pull-remote-db")


if __name__ == "__main__":
    unittest.main()
