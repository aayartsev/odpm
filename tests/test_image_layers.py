"""Unit tests for layered CI fingerprints and presence (ADR-027)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.image_layers.ensure import (
    _copy_deps_extra_addons,
    developing_project_path,
    ensure_deps,
    ensure_lint,
    run_layered_build,
)
from dev_project.image_layers.family import (
    FAMILY_DEV,
    FAMILY_RUNTIME,
    family_for_profile,
)
from dev_project.image_layers.fingerprint import (
    compute_deps_fingerprint,
    compute_lint_fingerprint,
    compute_platform_fingerprint,
    layer_image_ref,
)
from dev_project.image_layers.registry import (
    force_rebuild_requested,
    image_ref_exists,
)
from dev_project.prepare.sources_only import SOURCES_ONLY_STEP_IDS
from dev_project.project_env.types import MappedPath


class FamilyTests(unittest.TestCase):
    def test_full_is_dev_medium_is_runtime(self):
        self.assertEqual(family_for_profile("full"), FAMILY_DEV)
        self.assertEqual(family_for_profile("medium"), FAMILY_RUNTIME)
        self.assertEqual(family_for_profile("ci"), "ci")


class FingerprintTests(unittest.TestCase):
    def _config(self, *, profile: str = "full", project_dir: str | None = None):
        config = MagicMock()
        config.project_settings.odoo_version = "19.0"
        config.project_settings.odoo_build_date = "2026-01-01"
        config.project_settings.python_version = "3.12"
        config.project_settings.distro_name = "debian"
        config.project_settings.distro_version = "12"
        config.project_settings.arch = "amd64"
        config.project_settings.requirements_txt = ["foo", "bar"]
        config.project_dir = project_dir or "/tmp/proj"
        config.project_name = "demo"
        config.policy = MagicMock()
        config.policy.base_image_profile = profile
        config.policy.venv_mode = "baked"
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = None
        return config

    def test_platform_fingerprint_stable_and_profile_sensitive(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        cfg_full = self._config(profile="full")
        cfg_medium = self._config(profile="medium")
        with patch(
            "dev_project.image_layers.fingerprint._lock_sha_map",
            return_value={"platform": "abc123"},
        ):
            fp_full = compute_platform_fingerprint(cfg_full, program_dir=program_dir)
            fp_medium = compute_platform_fingerprint(
                cfg_medium, program_dir=program_dir
            )
            fp_full_2 = compute_platform_fingerprint(cfg_full, program_dir=program_dir)
        self.assertEqual(fp_full, fp_full_2)
        self.assertNotEqual(fp_full, fp_medium)
        ref_full = layer_image_ref(cfg_full, layer="platform", fingerprint=fp_full)
        ref_medium = layer_image_ref(
            cfg_medium, layer="platform", fingerprint=fp_medium
        )
        self.assertIn("-dev-", ref_full)
        self.assertIn("-runtime-", ref_medium)
        self.assertNotEqual(ref_full, ref_medium)

    def test_deps_fingerprint_none_without_dependencies(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        cfg = self._config()
        with patch(
            "dev_project.image_layers.fingerprint._lock_sha_map",
            return_value={"platform": "abc"},
        ):
            self.assertIsNone(
                compute_deps_fingerprint(
                    cfg, program_dir=program_dir, platform_ref="reg:plat"
                )
            )

    def test_deps_fingerprint_changes_with_oca_sha(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        cfg = self._config()
        with patch(
            "dev_project.image_layers.fingerprint._lock_sha_map",
            return_value={
                "platform": "abc",
                "https://github.com/OCA/web": "sha1",
            },
        ):
            fp1 = compute_deps_fingerprint(
                cfg, program_dir=program_dir, platform_ref="reg:plat"
            )
        with patch(
            "dev_project.image_layers.fingerprint._lock_sha_map",
            return_value={
                "platform": "abc",
                "https://github.com/OCA/web": "sha2",
            },
        ):
            fp2 = compute_deps_fingerprint(
                cfg, program_dir=program_dir, platform_ref="reg:plat"
            )
        self.assertIsNotNone(fp1)
        self.assertNotEqual(fp1, fp2)

    def test_lint_fingerprint_pre_commit_sensitive(self):
        program_dir = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
            cfg = self._config(project_dir=str(root))
            fp1 = compute_lint_fingerprint(
                cfg, program_dir=program_dir, platform_fp="plat1"
            )
            (root / ".pre-commit-config.yaml").write_text(
                "repos: [{repo: x}]\n", encoding="utf-8"
            )
            fp2 = compute_lint_fingerprint(
                cfg, program_dir=program_dir, platform_fp="plat1"
            )
            fp_plat = compute_lint_fingerprint(
                cfg, program_dir=program_dir, platform_fp="plat2"
            )
        self.assertNotEqual(fp1, fp2)
        self.assertNotEqual(fp2, fp_plat)

    def test_lint_fingerprint_bake_script_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            prog = root / "prog"
            bake = prog / "dev_project"
            bake.mkdir(parents=True)
            (bake / "templates").mkdir()
            (bake / "templates" / "dockerfile_lint").write_text(
                "FROM x\n", encoding="utf-8"
            )
            (bake / "bake_pre_commit.py").write_text("v1\n", encoding="utf-8")
            cfg = self._config(project_dir=str(root))
            fp1 = compute_lint_fingerprint(
                cfg, program_dir=str(prog), platform_fp="plat"
            )
            (bake / "bake_pre_commit.py").write_text("v2\n", encoding="utf-8")
            fp2 = compute_lint_fingerprint(
                cfg, program_dir=str(prog), platform_fp="plat"
            )
        self.assertNotEqual(fp1, fp2)

    def test_lint_template_has_no_extra_addons(self):
        root = Path(__file__).resolve().parents[1]
        lint = (root / "dev_project" / "templates" / "dockerfile_lint").read_text(
            encoding="utf-8"
        )
        ignore = (
            root / "dev_project" / "templates" / "dockerignore_lint"
        ).read_text(encoding="utf-8")
        self.assertNotIn("extra-addons", lint)
        self.assertIn("pre-commit", lint)
        self.assertIn("bake_pre_commit", lint)
        self.assertNotIn("install-hooks", lint)
        self.assertIn("USER ${CONTAINER_USER}", lint)
        # Hook cache must be written as the container user (~/.cache/pre-commit).
        user_idx = lint.index("USER ${CONTAINER_USER}")
        bake_idx = lint.index("python3 -m dev_project.bake_pre_commit")
        self.assertLess(user_idx, bake_idx)
        self.assertIn("!dev_project/", ignore)
        self.assertIn("!dev_project/bake_pre_commit.py", ignore)


class EnsureLintContextTests(unittest.TestCase):
    def _config(self, project_dir: str, program_dir: str):
        config = MagicMock()
        config.project_dir = project_dir
        config.program_dir = program_dir
        config.project_settings.odoo_version = "19.0"
        config.project_settings.odoo_build_date = "2026-01-01"
        config.project_settings.python_version = "3.12"
        config.project_settings.distro_name = "debian"
        config.project_settings.distro_version = "12"
        config.project_settings.arch = "amd64"
        config.project_settings.requirements_txt = []
        config.project_name = "demo"
        config.policy = MagicMock()
        config.policy.base_image_profile = "full"
        config.policy.venv_mode = "baked"
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = None
        return config

    @patch("dev_project.image_layers.ensure._build_image")
    @patch(
        "dev_project.image_layers.ensure.image_ref_exists",
        return_value=False,
    )
    @patch(
        "dev_project.image_layers.ensure.ensure_platform",
        return_value="registry/plat:tag",
    )
    @patch(
        "dev_project.image_layers.ensure.compute_platform_fingerprint",
        return_value="platfp",
    )
    def test_ensure_lint_prepares_context_from_program_dir(
        self,
        _plat_fp,
        _ensure_plat,
        _exists,
        mock_build,
    ):
        program_dir = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            (project / "developing").mkdir()
            (project / "developing" / "mod.py").write_text("x\n", encoding="utf-8")
            env = MagicMock()
            env.bootstrap = MagicMock(config=self._config(str(project), program_dir))
            args = OdpmCliArgs()
            ref = ensure_lint(env, args)
            self.assertTrue(ref)
            context = project / ".odpm" / "lint-build-context"
            self.assertTrue((context / ".pre-commit-config.yaml").is_file())
            self.assertTrue(
                (context / "dev_project" / "bake_pre_commit.py").is_file()
            )
            self.assertFalse((context / "developing").exists())
            dockerfile = (context / "Dockerfile.lint").read_text(encoding="utf-8")
            self.assertIn("bake_pre_commit.py", dockerfile)
            self.assertIn(".pre-commit-config.yaml", dockerfile)
            self.assertIn("python3 -m dev_project.bake_pre_commit", dockerfile)
            self.assertNotIn("extra-addons", dockerfile)
            mock_build.assert_called_once()

    @patch(
        "dev_project.image_layers.ensure.image_ref_exists",
        return_value=True,
    )
    @patch(
        "dev_project.image_layers.ensure.ensure_platform",
        return_value="registry/plat:tag",
    )
    @patch(
        "dev_project.image_layers.ensure.compute_platform_fingerprint",
        return_value="platfp",
    )
    @patch("dev_project.image_layers.ensure._build_image")
    def test_ensure_lint_skips_when_exists(
        self, mock_build, _plat_fp, _ensure_plat, _exists
    ):
        program_dir = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            env = MagicMock()
            env.bootstrap = MagicMock(config=self._config(str(project), program_dir))
            ensure_lint(env, OdpmCliArgs())
        mock_build.assert_not_called()


class RegistryPresenceTests(unittest.TestCase):
    def test_force_flag_is_miss_env_alone_is_not(self):
        with patch.dict("os.environ", {"ODPM_IMAGE_FORCE_REBUILD": "1"}, clear=False):
            self.assertTrue(force_rebuild_requested())
            # Nested parent checks must pass force=False explicitly.
            with patch(
                "dev_project.image_layers.registry._docker_image_exists",
                return_value=True,
            ):
                self.assertTrue(
                    image_ref_exists("any:tag", remote=False, force=False)
                )
            self.assertFalse(
                image_ref_exists("any:tag", remote=False, force=True)
            )

    @patch("dev_project.image_layers.registry.shutil.which", return_value=None)
    def test_remote_without_crane_raises(self, _which):
        with self.assertRaises(ConfigError):
            image_ref_exists("reg/img:tag", remote=True)


class DepsExcludeDevelopingTests(unittest.TestCase):
    def test_copy_deps_skips_developing_mapped_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oca = root / "oca_web"
            oca.mkdir()
            (oca / "mod").mkdir()
            developing = root / "my_app"
            developing.mkdir()
            (developing / "mod").mkdir()
            ctx = root / "ctx"
            (ctx / "extra-addons").mkdir(parents=True)

            config = MagicMock()
            config.docker_layout.docker_extra_addons = "/home/odoo/extra-addons"
            developing_link = MagicMock()
            developing_link.project_path = str(developing)
            config.developing_project = developing_link
            config.bootstrap = MagicMock()
            config.bootstrap.developing_project = developing_link

            env = MagicMock()
            env.bootstrap = MagicMock(config=config)
            env.mapped_folders = [
                MappedPath(
                    local=str(oca),
                    docker="/home/odoo/extra-addons/oca_web",
                ),
                MappedPath(
                    local=str(developing),
                    docker="/home/odoo/extra-addons/my_app",
                ),
            ]
            dest = root / "deps" / "extra-addons"
            copied = _copy_deps_extra_addons(
                env, full_ctx=ctx, dest_addons=dest
            )
            self.assertEqual(copied, 1)
            self.assertTrue((dest / "oca_web").is_dir())
            self.assertFalse((dest / "my_app").exists())

    def test_copy_deps_fallback_keeps_same_basename_dependency(self):
        """Basename-only skip must not drop an OCA tree named like developing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            developing = root / "elsewhere" / "web"
            developing.mkdir(parents=True)
            ctx_addons = root / "ctx" / "extra-addons"
            ctx_addons.mkdir(parents=True)
            oca_web = ctx_addons / "web"
            oca_web.mkdir()
            (oca_web / "module").mkdir()

            config = MagicMock()
            config.docker_layout.docker_extra_addons = "/home/odoo/extra-addons"
            developing_link = MagicMock()
            developing_link.project_path = str(developing)
            config.developing_project = developing_link
            config.bootstrap = MagicMock()
            config.bootstrap.developing_project = developing_link

            env = MagicMock()
            env.bootstrap = MagicMock(config=config)
            env.mapped_folders = []
            dest = root / "deps" / "extra-addons"
            copied = _copy_deps_extra_addons(
                env, full_ctx=root / "ctx", dest_addons=dest
            )
            self.assertEqual(copied, 1)
            self.assertTrue((dest / "web" / "module").is_dir())

    def test_developing_project_path_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            developing = Path(tmp) / "app"
            developing.mkdir()
            config = MagicMock()
            link = MagicMock()
            link.project_path = str(developing)
            config.developing_project = link
            self.assertEqual(
                developing_project_path(config), developing.resolve()
            )


class ForceRebuildScopeTests(unittest.TestCase):
    @patch.dict("os.environ", {"ODPM_IMAGE_FORCE_REBUILD": "1"}, clear=False)
    @patch("dev_project.image_layers.ensure.ensure_app")
    @patch("dev_project.image_layers.ensure.ensure_deps", return_value=None)
    @patch(
        "dev_project.image_layers.ensure.ensure_platform",
        return_value="reg:platform",
    )
    @patch("dev_project.image_layers.ensure.ensure_base", return_value="reg:base")
    def test_layered_build_forces_only_app(
        self, mock_base, mock_platform, mock_deps, mock_app
    ):
        env = MagicMock()
        args = OdpmCliArgs()
        mock_app.return_value = "reg:app"
        run_layered_build(env, args)
        mock_base.assert_called_once_with(env, force=False)
        mock_platform.assert_called_once_with(env, args, force=False)
        mock_deps.assert_called_once_with(
            env, args, platform_ref="reg:platform", force=False
        )
        mock_app.assert_called_once()
        self.assertTrue(mock_app.call_args.kwargs.get("force"))

    def test_ensure_base_force_rebuilds(self):
        from dev_project.image_layers.ensure import ensure_base

        env = MagicMock()
        env.bootstrap.config.project_dir = "/tmp/proj"
        builder = MagicMock()
        builder.resolve_base_image_ref.return_value = "base:tag"
        with (
            patch(
                "dev_project.project_env.base_image.BaseImageBuilder",
                return_value=builder,
            ),
            patch(
                "dev_project.project_env.services.BaseImageService"
            ) as mock_svc,
            patch(
                "dev_project.project_env.base_image_identity.base_image_identity_path",
                return_value="/tmp/proj/.odpm/base_image_identity.json",
            ),
            patch(
                "dev_project.project_env.base_image_identity.expected_base_image_identity",
                return_value={"uid": "1"},
            ),
            patch(
                "dev_project.project_env.base_image_identity.write_base_image_identity"
            ) as mock_write,
            patch.object(Path, "is_file", return_value=False),
        ):
            ref = ensure_base(env, force=True)
        self.assertEqual(ref, "base:tag")
        builder.build_base_image.assert_called_once()
        mock_svc.assert_not_called()
        mock_write.assert_called_once()


class PublishAliasTests(unittest.TestCase):
    def test_push_without_crane_and_nonlocal_cache_raises(self):
        from dev_project.image_layers.ensure import _publish_alias

        with (
            patch(
                "dev_project.image_layers.ensure.shutil.which",
                return_value=None,
            ),
            patch(
                "dev_project.image_layers.ensure.image_ref_exists",
                return_value=False,
            ),
        ):
            with self.assertRaises(ConfigError) as ctx:
                _publish_alias(
                    cache_ref="reg/cache:fp",
                    publish_tag="reg/app:final",
                    push=True,
                )
        msg = str(ctx.exception)
        self.assertIn("crane", msg.lower())
        self.assertIn("reg/cache:fp", msg)
        self.assertIn("reg/app:final", msg)

    def test_push_without_crane_uses_local_docker_when_cache_local(self):
        from dev_project.image_layers.ensure import _publish_alias

        with (
            patch(
                "dev_project.image_layers.ensure.shutil.which",
                return_value=None,
            ),
            patch(
                "dev_project.image_layers.ensure.image_ref_exists",
                return_value=True,
            ),
            patch(
                "dev_project.image_layers.ensure.retag_image"
            ) as mock_retag,
            patch(
                "dev_project.image_layers.ensure._docker_push_or_raise"
            ) as mock_push,
        ):
            _publish_alias(
                cache_ref="reg/cache:fp",
                publish_tag="reg/app:final",
                push=True,
            )
        mock_retag.assert_called_once_with(
            "reg/cache:fp", "reg/app:final", remote=False
        )
        mock_push.assert_called_once_with("reg/app:final")

    def test_push_with_crane_copies_remote(self):
        from dev_project.image_layers.ensure import _publish_alias

        with (
            patch(
                "dev_project.image_layers.ensure.shutil.which",
                return_value="/usr/bin/crane",
            ),
            patch(
                "dev_project.image_layers.ensure.retag_image"
            ) as mock_retag,
            patch(
                "dev_project.image_layers.ensure._docker_push_or_raise"
            ) as mock_push,
        ):
            _publish_alias(
                cache_ref="reg/cache:fp",
                publish_tag="reg/app:final",
                push=True,
            )
        mock_retag.assert_called_once_with(
            "reg/cache:fp", "reg/app:final", remote=True
        )
        mock_push.assert_not_called()


class PushPolicyTests(unittest.TestCase):
    def test_want_push_ignores_registry_env_alone(self):
        from dev_project.image_layers.ensure import _want_push

        config = MagicMock()
        args = OdpmCliArgs(image_push=False)
        with (
            patch.dict(
                "os.environ",
                {"CI_REGISTRY_IMAGE": "registry.example.com/proj"},
                clear=False,
            ),
            patch(
                "dev_project.image_layers.ensure.resolve_ci_image_push",
                return_value=False,
            ),
            patch(
                "dev_project.image_layers.ensure.environ_from_config",
                return_value={},
            ),
        ):
            self.assertFalse(_want_push(args, config))

    def test_want_push_true_when_flag_set(self):
        from dev_project.image_layers.ensure import _want_push

        config = MagicMock()
        args = OdpmCliArgs(image_push=True)
        with (
            patch(
                "dev_project.image_layers.ensure.resolve_ci_image_push",
                return_value=True,
            ),
            patch(
                "dev_project.image_layers.ensure.environ_from_config",
                return_value={},
            ),
        ):
            self.assertTrue(_want_push(args, config))

    def test_docker_push_or_raise_fails_fast(self):
        from dev_project.image_layers.ensure import _docker_push_or_raise

        with (
            patch(
                "dev_project.image_layers.ensure.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "dev_project.image_layers.ensure.subprocess.run",
                return_value=MagicMock(
                    returncode=1, stderr="denied", stdout=""
                ),
            ),
        ):
            with self.assertRaises(ConfigError) as ctx:
                _docker_push_or_raise("reg/app:tag")
        msg = str(ctx.exception)
        self.assertIn("reg/app:tag", msg)
        self.assertIn("denied", msg)


class DepsMissingTreesTests(unittest.TestCase):
    @patch(
        "dev_project.image_layers.ensure.compute_deps_fingerprint",
        return_value="deadbeef",
    )
    @patch(
        "dev_project.image_layers.ensure.image_ref_exists",
        return_value=False,
    )
    @patch("dev_project.image_layers.ensure._copy_deps_extra_addons", return_value=0)
    @patch.object(
        __import__(
            "dev_project.project_env.ci_image", fromlist=["CiImageBuilder"]
        ).CiImageBuilder,
        "prepare_ci_build_context",
    )
    def test_deps_raises_when_no_trees_after_filter(
        self, _prepare, _copy, _exists, _fp
    ):
        config = MagicMock()
        config.program_dir = str(Path(__file__).resolve().parents[1])
        config.project_dir = "/tmp/proj"
        config.project_name = "demo"
        config.project_settings.odoo_version = "19.0"
        config.project_settings.odoo_build_date = "2026-01-01"
        config.project_settings.arch = "amd64"
        config.docker_layout.ci_build_context_dir = "/tmp/proj/.odpm/ci-build-context"
        config.policy = MagicMock()
        config.policy.base_image_profile = "full"
        config.arguments = OdpmCliArgs()
        env = MagicMock()
        env.bootstrap = MagicMock(config=config)
        with self.assertRaises(ConfigError) as ctx:
            ensure_deps(
                env,
                OdpmCliArgs(),
                platform_ref="reg:platform",
                force=False,
            )
        self.assertIn("dependencies", str(ctx.exception).lower())


class SourcesOnlyIdsTests(unittest.TestCase):
    def test_whitelist_size(self):
        self.assertGreaterEqual(len(SOURCES_ONLY_STEP_IDS), 8)


class PruneCacheTagTests(unittest.TestCase):
    def test_parse_and_select_stale(self):
        from dev_project.image_layers.prune import (
            parse_cache_tag,
            select_stale_cache_tags,
            split_image_ref,
        )

        repo, tag = split_image_ref(
            "registry.example/proj:cache-app-dev-19.0-2026-01-01-v-aaaa1111"
        )
        self.assertEqual(repo, "registry.example/proj")
        prefix, fp = parse_cache_tag(tag)
        self.assertEqual(prefix, "cache-app-dev-19.0-2026-01-01-v-")
        self.assertEqual(fp, "aaaa1111")

        tags = [
            "cache-app-dev-19.0-2026-01-01-v-aaaa1111",
            "cache-app-dev-19.0-2026-01-01-v-bbbb2222",
            "cache-lint-dev-19.0-2026-01-01-v-aaaa1111",
            "cache-app-dev-19.0-2025-01-01-v-cccc3333",
            "mr-123",
            "latest",
        ]
        stale = select_stale_cache_tags(
            tags, keep_tag="cache-app-dev-19.0-2026-01-01-v-aaaa1111"
        )
        self.assertEqual(stale, ["cache-app-dev-19.0-2026-01-01-v-bbbb2222"])

    def test_prune_off_does_not_delete(self):
        from dev_project.image_layers.ensure import _maybe_prune_stale

        with patch(
            "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
        ) as mock_prune:
            _maybe_prune_stale(
                OdpmCliArgs(),
                "reg/proj:cache-app-dev-19.0-2026-01-01-v-aaaa",
                remote=False,
            )
        mock_prune.assert_not_called()

    def test_prune_cli_flag_calls_helper(self):
        from dev_project.image_layers.ensure import _maybe_prune_stale

        keep = "reg/proj:cache-app-dev-19.0-2026-01-01-v-aaaa"
        with patch(
            "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
        ) as mock_prune:
            _maybe_prune_stale(
                OdpmCliArgs(image_prune_stale=True),
                keep,
                remote=True,
            )
        mock_prune.assert_called_once_with(keep, remote=True)

    def test_prune_env_truthy(self):
        from dev_project.image_layers.prune import prune_stale_requested

        with patch.dict(
            "os.environ", {"ODPM_IMAGE_PRUNE_STALE": "1"}, clear=False
        ):
            self.assertTrue(prune_stale_requested(OdpmCliArgs()))
        with patch.dict(
            "os.environ", {"ODPM_IMAGE_PRUNE_STALE": "true"}, clear=False
        ):
            self.assertTrue(prune_stale_requested(OdpmCliArgs()))
        with patch.dict(
            "os.environ", {"ODPM_IMAGE_PRUNE_STALE": "0"}, clear=False
        ):
            self.assertFalse(prune_stale_requested(OdpmCliArgs()))

    @patch("dev_project.image_layers.prune.shutil.which", return_value=None)
    @patch("dev_project.image_layers.prune._docker_rmi")
    @patch(
        "dev_project.image_layers.prune._docker_list_tags",
        return_value=[
            "cache-platform-dev-19.0-2026-01-01-v-keepme01",
            "cache-platform-dev-19.0-2026-01-01-v-oldtag02",
        ],
    )
    def test_remote_without_crane_falls_back_to_local(
        self, _list, mock_rmi, _which
    ):
        from dev_project.image_layers.prune import prune_stale_layer_cache_tags

        keep = (
            "registry.example/proj:"
            "cache-platform-dev-19.0-2026-01-01-v-keepme01"
        )
        prune_stale_layer_cache_tags(keep, remote=True)
        mock_rmi.assert_called_once_with(
            "registry.example/proj:cache-platform-dev-19.0-2026-01-01-v-oldtag02"
        )

    @patch("dev_project.image_layers.prune.shutil.which")
    @patch("dev_project.image_layers.prune.subprocess.run")
    def test_crane_delete_error_is_soft(self, mock_run, mock_which):
        from dev_project.image_layers.prune import prune_stale_layer_cache_tags

        mock_which.side_effect = lambda name: (
            "/usr/bin/crane" if name == "crane" else None
        )

        def _run(cmd, **_kwargs):
            if cmd[1] == "ls":
                return MagicMock(
                    returncode=0,
                    stdout=(
                        "cache-app-dev-19.0-2026-01-01-v-keepme01\n"
                        "cache-app-dev-19.0-2026-01-01-v-oldtag02\n"
                    ),
                    stderr="",
                )
            return MagicMock(returncode=1, stdout="", stderr="denied")

        mock_run.side_effect = _run
        keep = (
            "registry.example/proj:cache-app-dev-19.0-2026-01-01-v-keepme01"
        )
        # Must not raise.
        prune_stale_layer_cache_tags(keep, remote=True)

    @patch(
        "dev_project.image_layers.ensure.image_ref_exists",
        return_value=True,
    )
    @patch(
        "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
    )
    def test_ensure_platform_hit_prunes_when_enabled(
        self, mock_prune, _exists
    ):
        from dev_project.image_layers.ensure import ensure_platform

        program_dir = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as tmp:
            env = MagicMock()
            env.bootstrap = MagicMock(config=MagicMock())
            env.bootstrap.config.program_dir = program_dir
            env.bootstrap.config.project_dir = tmp
            env.bootstrap.config.project_name = "demo"
            env.bootstrap.config.project_settings.odoo_version = "19.0"
            env.bootstrap.config.project_settings.odoo_build_date = "2026-01-01"
            env.bootstrap.config.project_settings.python_version = "3.12"
            env.bootstrap.config.project_settings.distro_name = "debian"
            env.bootstrap.config.project_settings.distro_version = "12"
            env.bootstrap.config.project_settings.arch = "amd64"
            env.bootstrap.config.policy = MagicMock()
            env.bootstrap.config.policy.base_image_profile = "full"
            env.bootstrap.config.project_settings.odoo_git_link = MagicMock()
            env.bootstrap.config.project_settings.odoo_git_link.commit = "abc"
            env.bootstrap.config.odoo_extra_deb_packages = []
            env.bootstrap.config.project_settings.requirements_txt = ""
            with (
                patch(
                    "dev_project.image_layers.ensure.compute_platform_fingerprint",
                    return_value="platfp01",
                ),
                patch(
                    "dev_project.image_layers.ensure.layer_image_ref",
                    return_value="reg/proj:cache-platform-dev-19.0-2026-01-01-v-platfp01",
                ),
                patch(
                    "dev_project.image_layers.ensure._remote_target",
                    return_value=False,
                ),
            ):
                ensure_platform(
                    env, OdpmCliArgs(image_prune_stale=True)
                )
        mock_prune.assert_called_once()
        self.assertEqual(
            mock_prune.call_args.args[0],
            "reg/proj:cache-platform-dev-19.0-2026-01-01-v-platfp01",
        )

    @patch(
        "dev_project.image_layers.ensure.compute_deps_fingerprint",
        return_value=None,
    )
    @patch(
        "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
    )
    def test_ensure_deps_skip_no_prune(self, mock_prune, _fp):
        env = MagicMock()
        env.bootstrap = MagicMock(config=MagicMock())
        env.bootstrap.config.program_dir = str(Path(__file__).resolve().parents[1])
        result = ensure_deps(
            env,
            OdpmCliArgs(image_prune_stale=True),
            platform_ref="reg:platform",
        )
        self.assertIsNone(result)
        mock_prune.assert_not_called()

    @patch("dev_project.image_layers.prune._crane_ls")
    @patch("dev_project.image_layers.prune._docker_rmi")
    @patch(
        "dev_project.image_layers.prune._docker_list_tags",
        return_value=[
            "cache-app-dev-19.0-2026-01-01-v-keepme01",
            "cache-app-dev-19.0-2026-01-01-v-oldtag02",
        ],
    )
    def test_local_only_does_not_call_crane(
        self, _list, mock_rmi, mock_crane_ls
    ):
        from dev_project.image_layers.prune import prune_stale_layer_cache_tags

        keep = (
            "odpm-local/demo:cache-app-dev-19.0-2026-01-01-v-keepme01"
        )
        prune_stale_layer_cache_tags(keep, remote=False)
        mock_crane_ls.assert_not_called()
        mock_rmi.assert_called_once_with(
            "odpm-local/demo:cache-app-dev-19.0-2026-01-01-v-oldtag02"
        )

    @patch(
        "dev_project.image_layers.ensure.image_ref_exists",
        return_value=False,
    )
    @patch("dev_project.image_layers.ensure.ensure_base", return_value="base:ref")
    @patch("dev_project.image_layers.ensure._build_image")
    @patch(
        "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
    )
    def test_ensure_platform_miss_prunes_after_build(
        self, mock_prune, mock_build, _base, _exists
    ):
        from dev_project.image_layers.ensure import ensure_platform

        program_dir = str(Path(__file__).resolve().parents[1])
        order: list[str] = []
        mock_build.side_effect = lambda **_kw: order.append("build")
        mock_prune.side_effect = lambda *_a, **_k: order.append("prune")
        keep = "reg/proj:cache-platform-dev-19.0-2026-01-01-v-platfp01"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ctx = project / ".odpm" / "ci-build-context"
            for name in ("odoo", "dev_project", "ci"):
                (ctx / name).mkdir(parents=True)
            env = MagicMock()
            env.bootstrap = MagicMock(config=MagicMock())
            env.bootstrap.config.program_dir = program_dir
            env.bootstrap.config.project_dir = str(project)
            env.bootstrap.config.project_name = "demo"
            env.bootstrap.config.project_settings.odoo_version = "19.0"
            env.bootstrap.config.project_settings.odoo_build_date = "2026-01-01"
            env.bootstrap.config.docker_layout.ci_build_context_dir = str(ctx)
            env.bootstrap.config.policy = MagicMock()
            env.bootstrap.config.policy.base_image_profile = "full"
            with (
                patch(
                    "dev_project.image_layers.ensure.compute_platform_fingerprint",
                    return_value="platfp01",
                ),
                patch(
                    "dev_project.image_layers.ensure.layer_image_ref",
                    return_value=keep,
                ),
                patch(
                    "dev_project.image_layers.ensure._remote_target",
                    return_value=False,
                ),
                patch(
                    "dev_project.image_layers.ensure._want_push",
                    return_value=False,
                ),
                patch(
                    "dev_project.image_layers.ensure._rewrite_from_line",
                    side_effect=lambda text, **_k: text,
                ),
                patch(
                    "dev_project.project_env.ci_image.CiImageBuilder.prepare_ci_build_context",
                ),
            ):
                def _copy_side_effect(_program_dir, _key, dest):
                    Path(dest).parent.mkdir(parents=True, exist_ok=True)
                    Path(dest).write_text("FROM scratch\n", encoding="utf-8")

                with patch(
                    "dev_project.image_layers.ensure._copy_template",
                    side_effect=_copy_side_effect,
                ):
                    ensure_platform(
                        env, OdpmCliArgs(image_prune_stale=True)
                    )
        self.assertEqual(order, ["build", "prune"])
        mock_prune.assert_called_once_with(keep, remote=False)

    @patch(
        "dev_project.image_layers.ensure.prune_stale_layer_cache_tags"
    )
    def test_ensure_app_passes_prune_flag_to_nested_platform(
        self, mock_prune
    ):
        """Nested ensure_platform gets the same args; hit-path prune is covered
        by test_ensure_platform_hit_prunes_when_enabled."""
        from dev_project.image_layers.ensure import ensure_app

        program_dir = str(Path(__file__).resolve().parents[1])
        plat_ref = (
            "reg/proj:cache-platform-dev-19.0-2026-01-01-v-platfp01"
        )
        app_ref = "reg/proj:cache-app-dev-19.0-2026-01-01-v-appfp001"
        with tempfile.TemporaryDirectory() as tmp:
            env = MagicMock()
            env.bootstrap = MagicMock(config=MagicMock())
            env.bootstrap.config.program_dir = program_dir
            env.bootstrap.config.project_dir = tmp
            env.bootstrap.config.project_name = "demo"
            env.bootstrap.config.project_settings.odoo_version = "19.0"
            env.bootstrap.config.project_settings.odoo_build_date = "2026-01-01"
            env.bootstrap.config.docker_layout.odoo_ci_image_name = "reg/proj:publish"
            env.bootstrap.config.policy = MagicMock()
            env.bootstrap.config.policy.base_image_profile = "full"
            env.bootstrap.config.developing_project = MagicMock()
            env.bootstrap.config.developing_project.project_path = tmp
            with (
                patch(
                    "dev_project.image_layers.ensure.ensure_deps",
                    return_value=None,
                ),
                patch(
                    "dev_project.image_layers.ensure.ensure_platform",
                    return_value=plat_ref,
                ) as mock_plat,
                patch(
                    "dev_project.image_layers.ensure._developing_git_sha",
                    return_value="deadbeef",
                ),
                patch(
                    "dev_project.image_layers.ensure.compute_app_fingerprint",
                    return_value="appfp001",
                ),
                patch(
                    "dev_project.image_layers.ensure.layer_image_ref",
                    return_value=app_ref,
                ),
                patch(
                    "dev_project.image_layers.ensure.image_ref_exists",
                    return_value=True,
                ),
                patch(
                    "dev_project.image_layers.ensure._remote_target",
                    return_value=False,
                ),
                patch(
                    "dev_project.image_layers.ensure._want_push",
                    return_value=False,
                ),
                patch(
                    "dev_project.image_layers.ensure._publish_alias",
                ),
            ):
                ensure_app(env, OdpmCliArgs(image_prune_stale=True))
        self.assertTrue(mock_plat.call_args.args[1].image_prune_stale)
        mock_prune.assert_called_once_with(app_ref, remote=False)


if __name__ == "__main__":
    unittest.main()
