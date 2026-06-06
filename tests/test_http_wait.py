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

    def test_wait_for_http_ok_retries_connection_reset(self) -> None:
        ready = MagicMock()
        ready.status = 200
        ready.__enter__ = lambda self: self
        ready.__exit__ = MagicMock(return_value=False)

        with patch(
            "tests.integration.http_wait.urllib.request.urlopen",
            side_effect=[ConnectionResetError(104, "Connection reset by peer"), ready],
        ):
            wait_for_http_ok(
                "http://127.0.0.1:8069/web",
                timeout=2.0,
                interval=0.1,
            )


if __name__ == "__main__":
    unittest.main()
