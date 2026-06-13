"""Tests for odpm host logging format."""

import logging
import unittest

from dev_project.logging import ODPM_LOG_TAG, CustomFormatter


class CustomFormatterTests(unittest.TestCase):
    def _format(self, level: int, *, use_color: bool) -> str:
        formatter = CustomFormatter(use_color=use_color)
        record = logging.LogRecord(
            name="dev_project.sample",
            level=level,
            pathname="sample.py",
            lineno=42,
            msg="hello",
            args=(),
            exc_info=None,
        )
        return formatter.format(record)

    def test_info_includes_odpm_tag_without_color(self) -> None:
        line = self._format(logging.INFO, use_color=False)
        self.assertIn(ODPM_LOG_TAG, line)
        self.assertIn("INFO", line)
        self.assertIn("hello", line)
        self.assertNotIn("\x1b[", line)

    def test_error_includes_odpm_tag_and_module_without_color(self) -> None:
        line = self._format(logging.ERROR, use_color=False)
        self.assertIn(ODPM_LOG_TAG, line)
        self.assertIn("ERROR", line)
        self.assertIn("dev_project.sample", line)
        self.assertIn("sample.py:42", line)

    def test_info_wraps_odpm_tag_in_color_when_enabled(self) -> None:
        line = self._format(logging.INFO, use_color=True)
        self.assertIn(ODPM_LOG_TAG, line)
        self.assertIn("\x1b[", line)
        self.assertIn("INFO", line)

    def test_error_uses_red_odpm_tag_when_color_enabled(self) -> None:
        line = self._format(logging.ERROR, use_color=True)
        self.assertIn("\x1b[31;1m" + ODPM_LOG_TAG, line)


if __name__ == "__main__":
    unittest.main()
