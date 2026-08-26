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
    manifest_trees_for_secret_ref_gate,
)
from dev_project.errors import ConfigError
from dev_project.manifest.reader import load_manifest
from dev_project.project_env.secrets import read_secrets_source, write_secrets_source


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

    def _reader_config(
        self,
        tmp: str,
        manifest: dict,
        *,
        scenario: str,
    ):
        developing = Path(tmp) / "developing"
        developing.mkdir(exist_ok=True)
        repo_json = developing / "odpm.json"
        repo_json.write_text(json.dumps(manifest), encoding="utf-8")
        project_link = Path(tmp) / "odpm.json"
        if project_link.exists() or project_link.is_symlink():
            project_link.unlink()
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
        config.user_env.odpm_scenario = scenario
        config.bootstrap = MagicMock()
        return config

    @staticmethod
    def _minimal_v2_platform() -> dict:
        return {
            "manifest_schema": 2,
            "requires_odpm": "4.4",
            "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
            "python": "3.12",
            "distro": {"name": "debian", "version": "13"},
            "postgres": "15",
        }

    def test_manifest_trees_gate_uses_effective_slice_not_other_scenarios(self):
        raw = {
            **self._minimal_v2_platform(),
            "scenarios": {
                "developer": {
                    "odoo_conf": {
                        "redis_server": {
                            "password": "${@secret:redis_password}",
                        },
                    },
                },
                "ci": {
                    "secrets": {"required": False},
                },
            },
        }
        ci_trees = manifest_trees_for_secret_ref_gate(raw, "ci")
        refs_ci: set[str] = set()
        from dev_project.config.transforms.env_substitution import (
            collect_secret_refs_in_value,
        )

        for tree in ci_trees:
            refs_ci.update(collect_secret_refs_in_value(tree))
        self.assertEqual(refs_ci, set())

        dev_trees = manifest_trees_for_secret_ref_gate(raw, "developer")
        refs_dev: set[str] = set()
        for tree in dev_trees:
            refs_dev.update(collect_secret_refs_in_value(tree))
        self.assertEqual(refs_dev, {"redis_password"})

    def test_odpm_json_reader_ci_ignores_developer_secret_refs(self):
        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader

        with tempfile.TemporaryDirectory() as tmp:
            manifest = {
                **self._minimal_v2_platform(),
                "scenarios": {
                    "developer": {
                        "secrets": {
                            "required": True,
                            "keys": ["redis_password", "minio_root_password"],
                        },
                        "odoo_conf": {
                            "redis_server": {
                                "password": "${@secret:redis_password}",
                            },
                            "s3_server": {
                                "secret_key": "${@secret:minio_root_password}",
                            },
                        },
                    },
                    "ci": {
                        "secrets": {"required": False},
                    },
                },
            }
            config = self._reader_config(tmp, manifest, scenario="ci")
            reader = OdpmJsonReader(config, rewrite_odpm_json=lambda: None)
            reader.get_odpm_settings()
            self.assertIsNotNone(config.bootstrap.manifest_view)

    def test_odpm_json_reader_developer_still_requires_secrets_for_overlay_refs(self):
        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader

        with tempfile.TemporaryDirectory() as tmp:
            manifest = {
                **self._minimal_v2_platform(),
                "scenarios": {
                    "developer": {
                        "odoo_conf": {
                            "redis_server": {
                                "password": "${@secret:redis_password}",
                            },
                        },
                    },
                    "ci": {"secrets": {"required": False}},
                },
            }
            config = self._reader_config(tmp, manifest, scenario="developer")
            reader = OdpmJsonReader(config, rewrite_odpm_json=lambda: None)
            with self.assertRaises(ConfigError) as ctx:
                reader.get_odpm_settings()
            self.assertIn("redis_password", str(ctx.exception))

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

    def test_odpm_json_reader_early_fetches_remote_then_expands_secret(self):
        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader
        from dev_project.host.cli.args import OdpmCliArgs
        from dev_project.secrets_providers.registry import (
            clear_secrets_providers_for_tests,
            register_secrets_provider,
        )
        from dev_project.secrets_providers.session import SecretsFetchSession

        class _Fake:
            name = "fake"

            def fetch(self, **_kwargs):
                return {"partner_armtek.armtek.apilogin": "from-provider"}

        register_secrets_provider(_Fake())
        self.addCleanup(clear_secrets_providers_for_tests)

        with tempfile.TemporaryDirectory() as tmp:
            manifest = {
                **self._minimal_v2_platform(),
                "secrets": {"provider": {"type": "fake"}},
                "services": {
                    "armtek": {
                        "image": "x",
                        "environment": {
                            "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                        },
                    }
                },
            }
            config = self._reader_config(tmp, manifest, scenario="developer")
            config.arguments = OdpmCliArgs(secrets_provider="fake")
            config.secrets_fetch_session = SecretsFetchSession()
            config.user_env.project_dotenv_dict.return_value = {}
            reader = OdpmJsonReader(config, rewrite_odpm_json=lambda: None)
            reader.get_odpm_settings()
            self.assertEqual(
                read_secrets_source(tmp)["partner_armtek.armtek.apilogin"],
                "from-provider",
            )
            view = config.bootstrap.manifest_view
            self.assertEqual(
                view.services["armtek"]["environment"]["APILOGIN"],
                "from-provider",
            )
            self.assertTrue(config.secrets_fetch_session.fetched)

    def test_odpm_json_reader_plan_without_secret_refs_skips_network(self):
        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader
        from dev_project.host.cli.args import OdpmCliArgs
        from dev_project.secrets_providers.session import SecretsFetchSession

        with tempfile.TemporaryDirectory() as tmp:
            manifest = {
                **self._minimal_v2_platform(),
                "secrets": {
                    "provider": {
                        "type": "infisical",
                        "project_id": "p",
                        "environment_slug": "dev",
                    }
                },
            }
            config = self._reader_config(tmp, manifest, scenario="developer")
            config.arguments = OdpmCliArgs(plan=True)
            config.secrets_fetch_session = SecretsFetchSession()
            config.user_env.project_dotenv_dict.return_value = {}
            reader = OdpmJsonReader(config, rewrite_odpm_json=lambda: None)
            with patch(
                "dev_project.secrets_providers.infisical_client.urllib.request.urlopen"
            ) as mock_urlopen:
                reader.get_odpm_settings()
            mock_urlopen.assert_not_called()
            self.assertFalse(config.secrets_fetch_session.fetched)
            self.assertIsNotNone(config.bootstrap.manifest_view)


if __name__ == "__main__":
    unittest.main()
