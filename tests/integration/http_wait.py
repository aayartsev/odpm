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
    accept_status_codes: set[int] | None = None,
) -> int:
    """Block until *url* returns an accepted status or *timeout* seconds elapse."""
    allowed = accept_status_codes if accept_status_codes is not None else {expected_status}
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=min(interval, 10.0)) as response:
                if response.status in allowed:
                    return response.status
                last_error = RuntimeError(
                    f"unexpected HTTP status {response.status} for {url} "
                    f"(allowed: {sorted(allowed)})"
                )
        except urllib.error.HTTPError as error:
            if error.code in allowed:
                return error.code
            last_error = error
        except urllib.error.URLError as error:
            last_error = error.reason if isinstance(error.reason, BaseException) else error
        except OSError as error:
            # Connection refused / reset while Odoo is still bootstrapping.
            last_error = error
        time.sleep(interval)
    allowed_text = ", ".join(str(code) for code in sorted(allowed))
    message = f"Timed out after {timeout}s waiting for HTTP {{{allowed_text}}} from {url}"
    if last_error is not None:
        raise HttpWaitTimeoutError(f"{message}: {last_error}") from last_error
    raise HttpWaitTimeoutError(message)
