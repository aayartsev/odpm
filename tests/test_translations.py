import os
import unittest

from dev_project.translations import _, update_locale


class GettextCatalogTests(unittest.TestCase):
    def tearDown(self) -> None:
        update_locale("en_US")

    def test_ru_locale_translates_known_strings(self):
        update_locale("ru_RU")
        self.assertEqual(_("Did you install git?"), "Вы установили git?")
        self.assertEqual(
            _("Running with sudo/root privileges is not permitted."),
            "Запуск скрипта от root/sudo запрещен",
        )
        self.assertIn(
            "сбросить настройки",
            _("If you want drop this file to default values, just delete it"),
        )

    def test_lc_all_env_selects_russian_catalog(self):
        update_locale("en_US")
        previous = os.environ.get("LC_ALL")
        os.environ["LC_ALL"] = "ru_RU.UTF-8"
        try:
            update_locale(os.environ["LC_ALL"])
            self.assertEqual(_("Did you install git?"), "Вы установили git?")
        finally:
            if previous is None:
                os.environ.pop("LC_ALL", None)
            else:
                os.environ["LC_ALL"] = previous
            update_locale("en_US")

    def test_unknown_msgid_falls_back_to_english(self):
        update_locale("ru_RU")
        msgid = "odpm gettext fallback probe string"
        self.assertEqual(_(msgid), msgid)


if __name__ == "__main__":
    unittest.main()
