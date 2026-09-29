"""Tests for dev_project.tools.http_download."""

from __future__ import annotations

import io
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from dev_project.errors import ConfigError
from dev_project.tools.http_download import (
    assert_odoo_backup_zip,
    download_multipart_post,
    safe_host_token,
)


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("dump.sql", "SELECT 1;\n")
    return buf.getvalue()


class HttpDownloadTests(unittest.TestCase):
    def test_safe_host_token(self):
        self.assertEqual(safe_host_token("https://client.example.com:8069/"), "client_example_com")
        self.assertEqual(safe_host_token("http://127.0.0.1"), "127_0_0_1")

    def test_download_multipart_post_writes_file(self):
        payload = _zip_bytes()

        def transport(request, timeout):
            self.assertEqual(request.get_method(), "POST")
            self.assertIn(b"master_pwd", request.data)
            self.assertEqual(timeout, 12.0)
            return io.BytesIO(payload)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.zip"
            result = download_multipart_post(
                "https://example.com/web/database/backup",
                dest,
                {"master_pwd": "secret", "name": "prod", "backup_format": "zip"},
                timeout=12.0,
                progress=False,
                transport=transport,
            )
            self.assertEqual(result, dest)
            self.assertTrue(dest.is_file())
            assert_odoo_backup_zip(dest)

    def test_assert_rejects_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.zip"
            path.write_text("<!DOCTYPE html><html>err</html>", encoding="utf-8")
            with self.assertRaises(ConfigError) as ctx:
                assert_odoo_backup_zip(path)
            self.assertIn("HTML", str(ctx.exception))

    def test_assert_rejects_non_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.zip"
            path.write_bytes(b"not-a-zip")
            with self.assertRaises(ConfigError) as ctx:
                assert_odoo_backup_zip(path)
            self.assertIn("not a zip", str(ctx.exception))

    def test_download_cleans_partial_on_http_error(self):
        import urllib.error

        def boom(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 500, "err", hdrs=None, fp=None  # type: ignore[arg-type]
            )

        # transport path doesn't use HTTPError from urlopen — test real path via mock urlopen
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.zip"
            with unittest.mock.patch(
                "dev_project.tools.http_download.urllib.request.urlopen",
                side_effect=urllib.error.HTTPError(
                    "https://x/y", 403, "Forbidden", hdrs=MagicMock(), fp=io.BytesIO(b"no")
                ),
            ):
                with self.assertRaises(ConfigError):
                    download_multipart_post(
                        "https://x/web/database/backup",
                        dest,
                        {"master_pwd": "x", "name": "db", "backup_format": "zip"},
                        progress=False,
                    )
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
