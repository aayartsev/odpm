import unittest

from tests.integration.compose_golden_patch import (
    patch_compose_for_golden_path,
    postgres_service_name_from_compose,
)

SAMPLE_COMPOSE = """\
services:
  db:
    image: postgres:17
    ports:
      - 5432:5432
    volumes:
      - postgres-data:/var/lib/postgresql/data

  odoo:
    image: odoo:test
    ports:
      - 8069:8069
      - 8072:8072
      - 5678:5678
    volumes:
      - ./data:/data

volumes:
  postgres-data:
"""

SAMPLE_COMPOSE_DB_DEV = """\
services:
  db-dev:
    image: postgres:17
    ports:
      - 5432:5432
    volumes:
      - postgres-data:/var/lib/postgresql/data

  odoo:
    image: odoo:test
    ports:
      - 8069:8069
      - 8072:8072
    depends_on:
      - db-dev

volumes:
  postgres-data:
"""


class ComposeGoldenPatchTests(unittest.TestCase):
    def test_removes_db_host_ports_and_remaps_odoo(self) -> None:
        patched = patch_compose_for_golden_path(SAMPLE_COMPOSE, 18099)
        self.assertNotIn("5432:5432", patched)
        self.assertNotIn("8072:8072", patched)
        self.assertNotIn("5678:5678", patched)
        self.assertIn("18099:8069", patched)
        self.assertIn("postgres-data:/var/lib/postgresql/data", patched)

    def test_removes_db_dev_host_ports(self) -> None:
        patched = patch_compose_for_golden_path(SAMPLE_COMPOSE_DB_DEV, 18099)
        self.assertNotIn("5432:5432", patched)
        self.assertIn("18099:8069", patched)
        self.assertIn("db-dev:", patched)

    def test_postgres_service_name_from_compose(self) -> None:
        self.assertEqual(
            postgres_service_name_from_compose(SAMPLE_COMPOSE_DB_DEV),
            "db-dev",
        )


if __name__ == "__main__":
    unittest.main()
