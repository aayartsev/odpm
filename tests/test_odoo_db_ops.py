import io
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project.inside_docker_app.exceptions import PostgresError
from dev_project.inside_docker_app.odoo_checker.db_ops import (
    DbCreationParams,
    OdooDbOps,
    normalize_country_code,
    sanitize_backup_basename,
)
from dev_project.inside_docker_app.odoo_checker.runtime import (
    LoadedOdooRuntime,
    apply_odoo_config,
)


def _creation_params(**overrides) -> DbCreationParams:
    defaults = dict(
        create_demo=True,
        db_lang="en_US",
        db_default_admin_password="admin",
        db_default_admin_login="admin",
        db_country_code="US",
    )
    defaults.update(overrides)
    return DbCreationParams(**defaults)


def _make_db_ops(
    *,
    odoo_dir: str = "/home/odoo/odoo",
    int_odoo_version: int = 19,
    creation: DbCreationParams | None = None,
) -> tuple[OdooDbOps, MagicMock]:
    odoo = MagicMock()
    ops = OdooDbOps(
        odoo,
        odoo_dir=odoo_dir,
        creation=creation or _creation_params(),
        int_odoo_version=int_odoo_version,
    )
    return ops, odoo


class SanitizeBackupBasenameTests(unittest.TestCase):
    def test_replaces_special_characters(self):
        self.assertEqual(
            sanitize_backup_basename("demo-db 01:00"),
            "demo_db_01_00",
        )


class NormalizeCountryCodeTests(unittest.TestCase):
    def test_none_and_false(self):
        self.assertIsNone(normalize_country_code(None))
        self.assertIsNone(normalize_country_code(False))
        self.assertIsNone(normalize_country_code(True))

    def test_empty_and_false_string(self):
        self.assertIsNone(normalize_country_code(""))
        self.assertIsNone(normalize_country_code("  "))
        self.assertIsNone(normalize_country_code("false"))
        self.assertIsNone(normalize_country_code("False"))

    def test_keeps_code(self):
        self.assertEqual(normalize_country_code("US"), "US")
        self.assertEqual(normalize_country_code("  ru  "), "ru")


class OdooDbOpsTests(unittest.TestCase):
    def test_backup_database_writes_dump_to_backup_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            odoo_dir = os.path.join(tmp_dir, "odoo")
            os.makedirs(odoo_dir)
            ops, odoo = _make_db_ops(odoo_dir=odoo_dir)
            odoo.service.db.dump_db.return_value = io.BytesIO(b"zip-data\n")

            path = ops.backup_database("demo-db", "manual-backup")

            self.assertEqual(path, os.path.join(tmp_dir, "backups", "manual-backup"))
            odoo.service.db.dump_db.assert_called_once_with(
                "demo-db", None, "zip"
            )
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), b"zip-data\n")

    def test_backup_database_generates_timestamped_name_for_bool_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            odoo_dir = os.path.join(tmp_dir, "odoo")
            os.makedirs(odoo_dir)
            ops, odoo = _make_db_ops(odoo_dir=odoo_dir)
            odoo.service.db.dump_db.return_value = io.BytesIO(b"x")

            path = ops.backup_database("demo", True)

            self.assertTrue(path.startswith(os.path.join(tmp_dir, "backups", "demo_")))
            self.assertTrue(os.path.isfile(path))

    def test_restore_database_resolves_path_under_backup_dir(self):
        ops, odoo = _make_db_ops()
        ops.restore_database("demo", "archive.zip")
        odoo.service.db.restore_db.assert_called_once_with(
            "demo",
            os.path.join(ops.backup_dir, "archive.zip"),
        )

    def test_drop_database_skips_when_missing(self):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.return_value = False

        ops.drop_database("missing", False)

        odoo.service.db.exp_drop.assert_not_called()

    @patch.object(OdooDbOps, "_force_drop_database")
    def test_drop_database_drops_existing_database(self, mock_force):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.side_effect = [True, False, False]
        odoo.service.db.exp_drop.return_value = True

        ops.drop_database("demo", False)

        odoo.service.db.exp_drop.assert_called_once_with("demo")
        mock_force.assert_not_called()

    @patch.object(OdooDbOps, "_force_drop_database")
    def test_drop_database_uses_db_name_when_flag_is_true(self, mock_force):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.side_effect = [True, False, False]
        odoo.service.db.exp_drop.return_value = True

        ops.drop_database(True, "demo")

        odoo.service.db.exp_drop.assert_called_once_with("demo")
        mock_force.assert_not_called()

    @patch.object(OdooDbOps, "_force_drop_database")
    def test_drop_database_force_drops_when_exp_drop_returns_false(self, mock_force):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.side_effect = [True, True, False]
        odoo.service.db.exp_drop.return_value = False

        ops.drop_database("demo", False)

        odoo.service.db.exp_drop.assert_called_once_with("demo")
        mock_force.assert_called_once_with("demo")

    @patch.object(OdooDbOps, "_force_drop_database")
    def test_drop_database_raises_when_still_exists(self, mock_force):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.return_value = True
        odoo.service.db.exp_drop.return_value = False

        with self.assertRaises(PostgresError):
            ops.drop_database("demo", False)

        mock_force.assert_called_once_with("demo")

    def test_get_list_of_databases_returns_newline_joined_names(self):
        ops, odoo = _make_db_ops()
        odoo.service.db.list_dbs.return_value = ["alpha", "beta"]

        result = ops.get_list_of_databases()

        self.assertEqual(result, "alpha\nbeta")
        odoo.service.db.list_dbs.assert_called_once_with(force=True)

    def test_ensure_database_exists_creates_missing_database(self):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.return_value = False

        ops.ensure_database_exists("demo")

        odoo.service.db.exp_create_database.assert_called_once_with(
            "demo",
            True,
            "en_US",
            user_password="admin",
            login="admin",
            country_code="US",
        )

    def test_ensure_database_exists_skips_existing_database(self):
        ops, odoo = _make_db_ops()
        odoo.service.db.exp_db_exist.return_value = True

        ops.ensure_database_exists("demo")

        odoo.service.db.exp_create_database.assert_not_called()


class OdooDbOpsV20Tests(unittest.TestCase):
    def test_ensure_database_exists_uses_modules_db_create(self):
        ops, odoo = _make_db_ops(int_odoo_version=20)
        odoo.modules.db.exist.return_value = False

        ops.ensure_database_exists("demo")

        odoo.modules.db.create.assert_called_once_with(
            "demo",
            demo=True,
            lang="en_US",
            user_password="admin",
            user_login="admin",
            country_code="US",
        )
        odoo.service.db.exp_create_database.assert_not_called()

    def test_ensure_database_exists_normalizes_empty_country_code(self):
        ops, odoo = _make_db_ops(
            int_odoo_version=20,
            creation=_creation_params(db_country_code=""),
        )
        odoo.modules.db.exist.return_value = False

        ops.ensure_database_exists("demo")

        odoo.modules.db.create.assert_called_once_with(
            "demo",
            demo=True,
            lang="en_US",
            user_password="admin",
            user_login="admin",
            country_code=None,
        )

    def test_ensure_database_exists_normalizes_false_country_code(self):
        ops, odoo = _make_db_ops(
            int_odoo_version=20,
            creation=_creation_params(db_country_code=False),
        )
        odoo.modules.db.exist.return_value = False

        ops.ensure_database_exists("demo")

        kwargs = odoo.modules.db.create.call_args.kwargs
        self.assertIsNone(kwargs["country_code"])

    def test_get_list_of_databases_uses_modules_db(self):
        ops, odoo = _make_db_ops(int_odoo_version=20)
        odoo.modules.db.list_dbs.return_value = ["alpha", "beta"]

        result = ops.get_list_of_databases()

        self.assertEqual(result, "alpha\nbeta")
        odoo.modules.db.list_dbs.assert_called_once_with(force=True)
        odoo.service.db.list_dbs.assert_not_called()

    def test_backup_database_uses_modules_db_dump(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            odoo_dir = os.path.join(tmp_dir, "odoo")
            os.makedirs(odoo_dir)
            ops, odoo = _make_db_ops(odoo_dir=odoo_dir, int_odoo_version=20)

            path = ops.backup_database("demo-db", "manual-backup")

            expected = os.path.join(tmp_dir, "backups", "manual-backup")
            self.assertEqual(path, expected)
            odoo.modules.db.dump.assert_called_once_with(
                "demo-db",
                expected,
                backup_format="zip",
            )
            odoo.service.db.dump_db.assert_not_called()

    def test_restore_database_uses_modules_db(self):
        ops, odoo = _make_db_ops(int_odoo_version=20)
        ops.restore_database("demo", "archive.zip")
        odoo.modules.db.restore.assert_called_once_with(
            "demo",
            os.path.join(ops.backup_dir, "archive.zip"),
        )
        odoo.service.db.restore_db.assert_not_called()

    def test_drop_database_uses_modules_db_drop(self):
        ops, odoo = _make_db_ops(int_odoo_version=20)
        odoo.modules.db.exist.side_effect = [True, False]

        with patch.object(OdooDbOps, "_force_drop_database") as mock_force:
            ops.drop_database("demo", False)

        odoo.modules.db.drop.assert_called_once_with("demo")
        odoo.service.db.exp_drop.assert_not_called()
        mock_force.assert_not_called()

    def test_drop_database_wraps_modules_db_errors(self):
        ops, odoo = _make_db_ops(int_odoo_version=20)
        odoo.modules.db.exist.return_value = True
        odoo.modules.db.drop.side_effect = RuntimeError("permission denied")

        with self.assertRaises(PostgresError) as ctx:
            ops.drop_database("demo", False)

        self.assertIn("demo", str(ctx.exception))


class ApplyOdooConfigLoggingTests(unittest.TestCase):
    def test_parse_config_setup_logging_true_for_odoo_20(self):
        odoo = MagicMock()
        runtime = LoadedOdooRuntime(
            odoo=odoo,
            odoo_config_object={},
            int_odoo_version=20,
            odoo_version_info=(20, 0),
            environment_manage=MagicMock(),
        )
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch(
                "dev_project.inside_docker_app.utils.write_odoo_config_data_to_file"
            ),
        ):
            conf_path = os.path.join(tmp_dir, "odoo.conf")
            apply_odoo_config(
                runtime,
                odoo_config_data={"options": {}},
                docker_path_odoo_conf=conf_path,
            )
        odoo.tools.config.parse_config.assert_called_once_with(
            ["-c", conf_path],
            setup_logging=True,
        )

    def test_parse_config_one_arg_for_odoo_19(self):
        odoo = MagicMock()
        runtime = LoadedOdooRuntime(
            odoo=odoo,
            odoo_config_object={},
            int_odoo_version=19,
            odoo_version_info=(19, 0),
            environment_manage=MagicMock(),
        )
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch(
                "dev_project.inside_docker_app.utils.write_odoo_config_data_to_file"
            ),
        ):
            conf_path = os.path.join(tmp_dir, "odoo.conf")
            apply_odoo_config(
                runtime,
                odoo_config_data={"options": {}},
                docker_path_odoo_conf=conf_path,
            )
        odoo.tools.config.parse_config.assert_called_once_with(["-c", conf_path])


if __name__ == "__main__":
    unittest.main()
