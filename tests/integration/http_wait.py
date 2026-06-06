"""Poll HTTP endpoints until success or timeout (golden-path E2E helper)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request


class HttpWaitTimeoutError(TimeoutError):
    """Raised when an HTTP endpoint did not become ready in time."""


def wait_for_http_ok(
    url: str,
    *,
    timeout: float = 300.0,
    interval: float = 2.0,
    expected_status: int = 200,
) -> None:
    """Block until *url* returns *expected_status* or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=min(interval, 10.0)) as response:
                if response.status == expected_status:
                    return
                last_error = RuntimeError(
                    f"unexpected HTTP status {response.status} for {url}"
                )
        except urllib.error.HTTPError as error:
            if error.code == expected_status:
                return
            last_error = error
        except urllib.error.URLError as error:
            last_error = error.reason if isinstance(error.reason, BaseException) else error
        except OSError as error:
            # Connection refused / reset while Odoo is still bootstrapping.
            last_error = error
        time.sleep(interval)
    message = f"Timed out after {timeout}s waiting for HTTP {expected_status} from {url}"
    if last_error is not None:
        raise HttpWaitTimeoutError(f"{message}: {last_error}") from last_error
    raise HttpWaitTimeoutError(message)
