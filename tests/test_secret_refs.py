"""Tests for ${@secret:} file gate and bootstrap wiring."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project.config.transforms.env_substitution import (
    EnvResolver,
    expand_env_in_compose_service_map,
    with_secrets,
)
from dev_project.config.transforms.secret_refs import (
    ensure_secrets_available_for_refs,
    load_secrets_map,
)
from dev_project.errors import ConfigError
from dev_project.manifest.reader import load_manifest
from dev_project.project_env.secrets import write_secrets_source


class SecretRefsGateTests(unittest.TestCase):
    def test_load_secrets_map_empty_without_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_secrets_map(tmp), {})

    def test_ensure_raises_when_refs_without_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError) as ctx:
                ensure_secrets_available_for_refs(
                    tmp,
                    {
                        "armtek": {
                            "environment": {
                                "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                            }
                        }
                    },
                )
            message = str(ctx.exception)
            self.assertIn("secrets.json", message)
            self.assertIn("--secrets-file", message)
            self.assertIn("partner_armtek.armtek.apilogin", message)

    def test_ensure_loads_when_file_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_secrets_source(
                tmp,
                {"partner_armtek.armtek.apilogin": "login"},
            )
            secrets = ensure_secrets_available_for_refs(
                tmp,
                {
                    "armtek": {
                        "environment": {
                            "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                        }
                    }
                },
            )
            self.assertEqual(secrets["partner_armtek.armtek.apilogin"], "login")

    def test_ensure_noop_without_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ensure_secrets_available_for_refs(tmp, {"x": 1}), {})

    def test_load_manifest_expands_secret_with_resolver(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"partner_armtek.armtek.apilogin": "u1"},
        )
        view = load_manifest(
            {
                "manifest_schema": 2,
                "requires_odpm": "4.4",
                "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
                "python": "3.12",
                "distro": {"name": "debian", "version": "13"},
                "postgres": "15",
                "services": {
                    "armtek": {
                        "image": "armtek:latest",
                        "environment": {
                            "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                        },
                    }
                },
            },
            env_resolver=resolver,
        )
        self.assertEqual(
            view.services["armtek"]["environment"]["APILOGIN"],
            "u1",
        )

    def test_bootstrap_init_context_attaches_secrets(self):
        from dev_project.config.bootstrap import init_context
        from dev_project.host.cli.args import OdpmCliArgs

        with tempfile.TemporaryDirectory() as tmp:
            write_secrets_source(tmp, {"api.key": "secret-value"})
            config = MagicMock()
            pd_manager = MagicMock()
            pd_manager.project_path = tmp
            pd_manager.home_config_dir = tmp
            user_env = MagicMock()
            user_env.odpm_scenario = "developer"
            user_env.project_dotenv_dict.return_value = {}
            user_env.compose_prefix = ""
            user_env.postgres_service_name = "db"

            with patch(
                "dev_project.config.bootstrap.DevelopingRepoMaterializer"
            ), patch(
                "dev_project.config.bootstrap.ConfigBootstrapContext"
            ) as mock_ctx_cls:
                mock_ctx = MagicMock()
                mock_ctx.paths.get_postgres_data_local_storage_path.return_value = tmp
                mock_ctx_cls.return_value = mock_ctx
                init_context(
                    config,
                    pd_manager,
                    OdpmCliArgs(),
                    "/opt/odpm",
                    user_env,
                )

            self.assertEqual(
                config._env_resolver.secrets.get("api.key"),
                "secret-value",
            )

    def test_odpm_json_reader_gates_missing_secrets_file(self):
        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader

        with tempfile.TemporaryDirectory() as tmp:
            developing = Path(tmp) / "developing"
            developing.mkdir()
            manifest = {
                "manifest_schema": 2,
                "requires_odpm": "4.4",
                "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
                "python": "3.12",
                "distro": {"name": "debian", "version": "13"},
                "postgres": "15",
                "services": {
                    "armtek": {
                        "image": "x",
                        "environment": {
                            "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                        },
                    }
                },
            }
            repo_json = developing / "odpm.json"
            repo_json.write_text(json.dumps(manifest), encoding="utf-8")
            project_link = Path(tmp) / "odpm.json"
            project_link.symlink_to(repo_json)

            config = MagicMock()
            config.project_dir = tmp
            config.repo_odpm_json = str(repo_json)
            config.project_odpm_json = str(project_link)
            config.developing_project.project_path = str(developing)
            config.env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
            )
            config.user_env.odpm_scenario = "developer"
            config.bootstrap = MagicMock()

            reader = OdpmJsonReader(config, rewrite_odpm_json=lambda: None)
            with self.assertRaises(ConfigError) as ctx:
                reader.get_odpm_settings()
            self.assertIn("secrets.json", str(ctx.exception))

    def test_inject_preserves_secrets_for_compose_reexpand(self):
        from dev_project.config.transforms.env_substitution import (
            inject_service_source_paths,
        )

        resolver = with_secrets(
            EnvResolver.from_sources(process_environ={}, project_dotenv={}),
            {"api.key": "v"},
        )
        injected = inject_service_source_paths(
            resolver, {"autoparts_env": "/tmp/src"}
        )
        expanded = expand_env_in_compose_service_map(
            {
                "armtek": {
                    "image": "x",
                    "environment": {"TOKEN": "${@secret:api.key}"},
                    "volumes": ["${@source:autoparts_env}/data:/data"],
                }
            },
            resolver=injected,
            field_prefix="services",
        )
        self.assertEqual(expanded["armtek"]["environment"]["TOKEN"], "v")
        self.assertEqual(expanded["armtek"]["volumes"], ["/tmp/src/data:/data"])

    def test_hook_argv_expands_secret(self):
        from dev_project.extensions.hooks import _expand_hook_argv

        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"partner_armtek.armtek.apilogin": "login"},
        )
        argv = _expand_hook_argv(
            ("echo", "${@secret:partner_armtek.armtek.apilogin}"),
            resolver=resolver,
            phase="post_prepare",
            command_index=0,
        )
        self.assertEqual(argv, ("echo", "login"))


if __name__ == "__main__":
    unittest.main()
