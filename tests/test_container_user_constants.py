import platform
import unittest

from dev_project import constants


class ContainerUserConstantsTests(unittest.TestCase):
    def test_container_user_is_always_odoo(self):
        self.assertEqual(constants.CONTAINER_USER, "odoo")
        self.assertEqual(constants.CONTAINER_USER_UID, "9999")
        self.assertEqual(constants.CONTAINER_USER_GID, "9999")
        self.assertEqual(constants.POSTGRES_ODOO_USER, "odoo")

    def test_current_user_aliases_container_user(self):
        self.assertEqual(constants.CURRENT_USER, constants.CONTAINER_USER)
        self.assertEqual(constants.CURRENT_USER_UID, constants.CONTAINER_USER_UID)

    @unittest.skipUnless(platform.system() == "Linux", "host user detection is Linux-specific")
    def test_host_user_on_linux_differs_from_container_when_not_odoo(self):
        import getpass

        login = getpass.getuser()
        if login == "odoo":
            self.skipTest("running as odoo; cannot assert host/container split")
        self.assertEqual(constants.CONTAINER_USER, "odoo")
        self.assertEqual(constants.HOST_USER, login)


if __name__ == "__main__":
    unittest.main()
