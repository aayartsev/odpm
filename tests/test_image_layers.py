"""Unit tests for layered CI fingerprints and presence (ADR-027)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from dev_project.image_layers.registry import image_ref_exists
from dev_project.prepare.sources_only import SOURCES_ONLY_STEP_IDS


class FamilyTests(unittest.TestCase):
    def test_full_is_dev_medium_is_runtime(self):
        self.assertEqual(family_for_profile("full"), FAMILY_DEV)
        self.assertEqual(family_for_profile("medium"), FAMILY_RUNTIME)
        self.assertEqual(family_for_profile("ci"), "ci")


class FingerprintTests(unittest.TestCase):
    def _config(self, *, profile: str = "full", project_dir: str | None = None):
        config = MagicMock()
        config.odoo_version = "19.0"
        config.odoo_build_date = "2026-01-01"
        config.python_version = "3.12"
        config.distro_name = "debian"
        config.distro_version = "12"
        config.arch = "amd64"
        config.requirements_txt = ["foo", "bar"]
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

    def test_lint_template_has_no_extra_addons(self):
        root = Path(__file__).resolve().parents[1]
        lint = (root / "dev_project" / "templates" / "dockerfile_lint").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("extra-addons", lint)
        self.assertIn("pre-commit", lint)


class RegistryPresenceTests(unittest.TestCase):
    @patch.dict("os.environ", {"ODPM_IMAGE_FORCE_REBUILD": "1"}, clear=False)
    def test_force_rebuild_is_miss(self):
        self.assertFalse(image_ref_exists("any:tag", remote=False))

    @patch("dev_project.image_layers.registry.shutil.which", return_value=None)
    def test_remote_without_crane_raises(self, _which):
        from dev_project.errors import ConfigError

        with self.assertRaises(ConfigError):
            image_ref_exists("reg/img:tag", remote=True)


class SourcesOnlyIdsTests(unittest.TestCase):
    def test_whitelist_size(self):
        self.assertGreaterEqual(len(SOURCES_ONLY_STEP_IDS), 8)


if __name__ == "__main__":
    unittest.main()
