import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock, patch

from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/web":
            self.send_response(200)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return


class HttpWaitTests(unittest.TestCase):
    def test_wait_for_http_ok_succeeds_when_server_ready(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _OkHandler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            wait_for_http_ok(
                f"http://{host}:{port}/web",
                timeout=5.0,
                interval=0.2,
            )
        finally:
            server.shutdown()

    def test_wait_for_http_ok_times_out(self) -> None:
        with self.assertRaises(HttpWaitTimeoutError):
            wait_for_http_ok(
                "http://127.0.0.1:1/web",
                timeout=0.5,
                interval=0.1,
            )

    def test_wait_for_http_ok_accepts_multiple_status_codes(self) -> None:
        class _MultiHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(500)
                self.end_headers()

            def log_message(self, _format: str, *_args) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), _MultiHandler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status = wait_for_http_ok(
                f"http://{host}:{port}/web/login",
                timeout=5.0,
                interval=0.2,
                accept_status_codes={200, 500},
            )
            self.assertEqual(status, 500)
        finally:
            server.shutdown()

    def test_wait_for_http_ok_accepts_redirect_without_following(self) -> None:
        class _RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(303)
                self.send_header("Location", "/web/database/selector")
                self.end_headers()
                self.wfile.write(b"see other")

            def log_message(self, _format: str, *_args) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), _RedirectHandler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status = wait_for_http_ok(
                f"http://{host}:{port}/web/login",
                timeout=5.0,
                interval=0.2,
                accept_status_codes={200, 303},
            )
            self.assertEqual(status, 303)
        finally:
            server.shutdown()

    def test_wait_for_http_ok_timeout_includes_body_snippet(self) -> None:
        class _ForbiddenHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden by policy")

            def log_message(self, _format: str, *_args) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), _ForbiddenHandler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(HttpWaitTimeoutError) as raised:
                wait_for_http_ok(
                    f"http://{host}:{port}/web/login",
                    timeout=0.6,
                    interval=0.2,
                    accept_status_codes={200},
                )
        finally:
            server.shutdown()
        message = str(raised.exception)
        self.assertIn("403", message)
        self.assertIn("Forbidden by policy", message)

    def test_wait_for_http_ok_retries_connection_reset(self) -> None:
        ready = MagicMock()
        ready.status = 200
        ready.__enter__ = lambda self: self
        ready.__exit__ = MagicMock(return_value=False)

        with patch(
            "tests.integration.http_wait._NO_REDIRECT_OPENER.open",
            side_effect=[ConnectionResetError(104, "Connection reset by peer"), ready],
        ):
            wait_for_http_ok(
                "http://127.0.0.1:8069/web",
                timeout=2.0,
                interval=0.1,
            )


if __name__ == "__main__":
    unittest.main()
