import unittest

from dev_project import host_summaries
from dev_project.translations import _, update_locale


class HumanSummaryLocaleTests(unittest.TestCase):
    def tearDown(self) -> None:
        update_locale("en_US")

    def test_ru_human_summaries(self):
        update_locale("ru_RU")
        self.assertIn(
            "Подготовка окружения",
            _(host_summaries.MSG_PREPARE_STARTED),
        )
        self.assertIn(
            "Файлы проекта готовы",
            _(host_summaries.MSG_PREPARE_COMPLETED),
        )
        self.assertIn(
            "Запуск контейнеров",
            _(host_summaries.MSG_STARTING_CONTAINERS),
        )
        self.assertIn(
            "английском",
            _(host_summaries.MSG_CONTAINER_LOGS_ENGLISH),
        )
        self.assertEqual(
            _(host_summaries.MSG_ODOO_URL_HINT).format(ODOO_PORT=8069),
            "Когда Odoo будет готов, откройте http://localhost:8069",
        )
        self.assertIn(
            "docker compose ps",
            _(host_summaries.MSG_COMPOSE_FAILED_HINT),
        )

    def test_summary_msgid_count(self):
        self.assertGreaterEqual(len(host_summaries.SUMMARY_MSGIDS), 8)


if __name__ == "__main__":
    unittest.main()
