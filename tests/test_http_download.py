"""Tests for dev_project.tools.http_download."""

from __future__ import annotations

import io
import json
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
    list_remote_odoo_databases,
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

    def test_list_remote_odoo_databases(self):
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": "1", "result": ["prod", "staging"]}
        ).encode("utf-8")

        def transport(request, timeout):
            self.assertIn("/web/database/list", request.full_url)
            self.assertEqual(request.get_method(), "POST")
            return io.BytesIO(payload)

        names = list_remote_odoo_databases(
            "https://example.com",
            transport=transport,
        )
        self.assertEqual(names, ["prod", "staging"])

    def test_list_remote_odoo_databases_raises_on_error(self):
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "error": {"message": "Access Denied"},
            }
        ).encode("utf-8")

        def transport(request, timeout):
            return io.BytesIO(payload)

        with self.assertRaises(ConfigError) as ctx:
            list_remote_odoo_databases("https://example.com", transport=transport)
        self.assertIn("Access Denied", str(ctx.exception))

    def test_download_multipart_post_writes_file(self):
        payload = _zip_bytes()
        headers_seen: list[dict[str, str]] = []
        progress_seen: list[tuple[int, int | None]] = []

        def transport(request, timeout):
            self.assertEqual(request.get_method(), "POST")
            self.assertIn(b"master_pwd", request.data)
            self.assertEqual(timeout, 12.0)
            stream = io.BytesIO(payload)
            stream.headers = {"Content-Type": "application/octet-stream"}  # type: ignore[attr-defined]
            return stream

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.zip"
            result = download_multipart_post(
                "https://example.com/web/database/backup",
                dest,
                {"master_pwd": "secret", "name": "prod", "backup_format": "zip"},
                timeout=12.0,
                progress=False,
                transport=transport,
                on_response_headers=lambda h: headers_seen.append(dict(h)),
                on_progress=lambda total, length: progress_seen.append((total, length)),
            )
            self.assertEqual(result, dest)
            self.assertTrue(dest.is_file())
            assert_odoo_backup_zip(dest)
            self.assertEqual(len(headers_seen), 1)
            self.assertTrue(progress_seen)
            self.assertEqual(progress_seen[-1][0], dest.stat().st_size)

    def test_download_rejects_html_content_type(self):
        html = b"<!DOCTYPE html><html>Database backup error: wrong password</html>"

        def transport(request, timeout):
            stream = io.BytesIO(html)
            stream.headers = {"Content-Type": "text/html; charset=utf-8"}  # type: ignore[attr-defined]
            return stream

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.zip"
            with self.assertRaises(ConfigError) as ctx:
                download_multipart_post(
                    "https://example.com/web/database/backup",
                    dest,
                    {"master_pwd": "x", "name": "db", "backup_format": "zip"},
                    progress=False,
                    transport=transport,
                )
            self.assertIn("wrong password", str(ctx.exception).lower())
            self.assertFalse(dest.exists())

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
