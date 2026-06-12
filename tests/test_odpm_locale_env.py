import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.cli import main
from dev_project.host.locale_bootstrap import (
    bootstrap_host_locale,
    read_odpm_locale_from_env_file,
)
from dev_project.host.user_env import CreateUserEnvironment
from dev_project.project_dir_manager import ProjectDirManager
from dev_project.translations import _, resolve_effective_locale, update_locale
from tests.cli_test_helpers import cli_args


def _program_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_pd_manager(project_dir: str, *, home_dir: str) -> ProjectDirManager:
    os.makedirs(
        os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
        exist_ok=True,
    )
    args = cli_args(odoo_git_link=None)
    with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
        return ProjectDirManager(project_dir, args, _program_dir())


def _write_env_file(
    path: str,
    *,
    odpm_locale: str | None = None,
    backups: str = "/tmp/backups",
    projects: str = "/tmp/projects",
    scenario: str = constants.DEVELOPER_SCENARIO,
) -> None:
    lines = [
        f"BACKUP_DIR={backups}",
        f"ODOO_PROJECTS_DIR={projects}",
        "PATH_TO_SSH_KEY=",
        "ODOO_PORT=8069",
        "POSTGRES_PORT=5432",
        "DEBUGGER_PORT=5678",
        "GEVENT_PORT=8072",
        f"ODPM_SCENARIO={scenario}",
    ]
    if odpm_locale is not None:
        lines.append(f"ODPM_LOCALE={odpm_locale}")
    with open(path, "w", encoding="utf-8") as writer:
        writer.write("\n".join(lines) + "\n")


class ResolveEffectiveLocaleTests(unittest.TestCase):
    def tearDown(self) -> None:
        update_locale("en_US")

    def test_file_locale_overrides_lang(self) -> None:
        environ = {"LANG": "ru_RU.UTF-8", "ODPM_LOCALE": "en_US"}
        self.assertEqual(
            resolve_effective_locale("en_US", environ=environ),
            "en_US",
        )

    def test_empty_file_locale_uses_lang(self) -> None:
        environ = {"LANG": "ru_RU.UTF-8"}
        self.assertEqual(resolve_effective_locale(None, environ=environ), "ru_RU")

    def test_process_env_locale_used_when_file_missing(self) -> None:
        environ = {"ODPM_LOCALE": "ru_RU", "LANG": "en_US.UTF-8"}
        self.assertEqual(resolve_effective_locale(None, environ=environ), "ru_RU")

    def test_invalid_locale_falls_back_to_lang(self) -> None:
        environ = {"ODPM_LOCALE": "not-a-locale", "LANG": "ru_RU.UTF-8"}
        self.assertEqual(resolve_effective_locale(None, environ=environ), "ru_RU")


class CreateUserEnvironmentLocaleTests(unittest.TestCase):
    def tearDown(self) -> None:
        update_locale("en_US")

    def test_project_env_locale_applies_russian_messages(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            _write_env_file(project_env, odpm_locale="ru_RU")
            with patch.dict(os.environ, {"HOME": home_dir, "LANG": "C"}, clear=True):
                pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
                CreateUserEnvironment(pd_manager)
            self.assertEqual(_("Did you install git?"), "Вы установили git?")

    def test_empty_locale_key_uses_lang(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            _write_env_file(project_env, odpm_locale="")
            with patch.dict(
                os.environ,
                {"HOME": home_dir, "LANG": "ru_RU.UTF-8"},
                clear=True,
            ):
                pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
                CreateUserEnvironment(pd_manager)
            self.assertEqual(_("Did you install git?"), "Вы установили git?")

    def test_unsupported_locale_falls_back_to_english_msgid(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            _write_env_file(project_env, odpm_locale="de_DE")
            with patch.dict(os.environ, {"HOME": home_dir, "LANG": "ru_RU.UTF-8"}, clear=True):
                pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
                CreateUserEnvironment(pd_manager)
            self.assertEqual(_("Did you install git?"), "Did you install git?")


class LocaleBootstrapTests(unittest.TestCase):
    def tearDown(self) -> None:
        update_locale("en_US")

    def test_read_odpm_locale_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = os.path.join(tmp_dir, constants.ENV_FILE_NAME)
            _write_env_file(env_path, odpm_locale="ru_RU")
            self.assertEqual(read_odpm_locale_from_env_file(env_path), "ru_RU")

    def test_bootstrap_host_locale_applies_project_env(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            _write_env_file(
                os.path.join(project_dir, constants.ENV_FILE_NAME),
                odpm_locale="ru_RU",
            )
            with patch.dict(os.environ, {"LANG": "C"}, clear=True):
                previous_cwd = os.getcwd()
                try:
                    os.chdir(project_dir)
                    bootstrap_host_locale(project_dir)
                finally:
                    os.chdir(previous_cwd)
            self.assertEqual(_("Did you install git?"), "Вы установили git?")

    @patch("dev_project.cli.OdpmPipeline")
    @patch("dev_project.cli.parse_cli_args")
    def test_main_root_guard_uses_project_env_locale(
        self,
        mock_parse_args,
        mock_pipeline,
    ) -> None:
        mock_parse_args.return_value = cli_args(odoo_git_link=None)
        with tempfile.TemporaryDirectory() as project_dir:
            _write_env_file(
                os.path.join(project_dir, constants.ENV_FILE_NAME),
                odpm_locale="ru_RU",
            )
            previous_cwd = os.getcwd()
            try:
                os.chdir(project_dir)
                with patch.dict(os.environ, {"LANG": "C"}, clear=True):
                    with patch.object(os, "geteuid", return_value=0, create=True):
                        with self.assertRaises(SystemExit) as ctx:
                            main()
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(ctx.exception.code, 1)
            mock_parse_args.assert_not_called()
            mock_pipeline.assert_not_called()
            self.assertEqual(
                _("Running with sudo/root privileges is not permitted."),
                "Запуск скрипта от root/sudo запрещен",
            )


class NonInteractiveLocaleEnvTests(unittest.TestCase):
    @patch("dev_project.host.user_env.stdin_is_interactive", return_value=False)
    def test_noninteractive_writes_odpm_locale_from_environment(self, _mock_tty) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            env = {
                "HOME": home_dir,
                "BACKUP_DIR": "/tmp/backups",
                "ODOO_PROJECTS_DIR": "/tmp/projects",
                "ODPM_SCENARIO": constants.CI_SCENARIO,
                "ODPM_LOCALE": "ru_RU",
            }
            with patch.dict(os.environ, env, clear=True):
                CreateUserEnvironment(pd_manager)

            env_file = (
                Path(home_dir) / constants.CONFIG_DIR_IN_HOME_DIR / constants.ENV_FILE_NAME
            )
            content = env_file.read_text(encoding="utf-8")
            self.assertIn("ODPM_LOCALE=ru_RU", content)

    @patch("dev_project.host.user_env.stdin_is_interactive", return_value=False)
    def test_noninteractive_omits_odpm_locale_without_environment(self, _mock_tty) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            env = {
                "HOME": home_dir,
                "BACKUP_DIR": "/tmp/backups",
                "ODOO_PROJECTS_DIR": "/tmp/projects",
                "ODPM_SCENARIO": constants.CI_SCENARIO,
            }
            with patch.dict(os.environ, env, clear=True):
                CreateUserEnvironment(pd_manager)

            env_file = (
                Path(home_dir) / constants.CONFIG_DIR_IN_HOME_DIR / constants.ENV_FILE_NAME
            )
            content = env_file.read_text(encoding="utf-8")
            self.assertNotIn("ODPM_LOCALE", content)


class InteractiveLocaleWizardTests(unittest.TestCase):
    @patch("dev_project.host.user_env.stdin_is_interactive", return_value=True)
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_backup_dir",
        return_value="/tmp/backups",
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_odoo_projects_src_dir",
        return_value="/tmp/projects",
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_odoo_port",
        return_value=8069,
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_postgres_port",
        return_value=5432,
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_debugger_port",
        return_value=5678,
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_gevent_port",
        return_value=8072,
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_odpm_scenario",
        return_value=constants.DEVELOPER_SCENARIO,
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_odpm_ide",
        return_value="vscode",
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_debugger_backend",
        return_value="debugpy_listen",
    )
    @patch(
        "dev_project.host.user_env.CreateUserEnvironment.get_from_user_odpm_locale",
        return_value="ru_RU",
    )
    def test_interactive_env_file_includes_locale(
        self,
        _mock_locale,
        _mock_debugger_backend,
        _mock_odpm_ide,
        _mock_scenario,
        _mock_gevent,
        _mock_debugger,
        _mock_postgres,
        _mock_odoo,
        _mock_projects,
        _mock_backup,
        _mock_tty,
    ) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(pd_manager)
            content = Path(user_env.env_file).read_text(encoding="utf-8")
            self.assertIn("ODPM_LOCALE=ru_RU", content)
            self.assertIn("PATH_TO_SSH_KEY=", content)


if __name__ == "__main__":
    unittest.main()
