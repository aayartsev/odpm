"""Poll HTTP endpoints until success or timeout (golden-path E2E helper)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request


class HttpWaitTimeoutError(TimeoutError):
    """Raised when an HTTP endpoint did not become ready in time."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Surface 3xx as ``HTTPError`` so callers can accept redirect statuses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _http_error_detail(error: urllib.error.HTTPError) -> str:
    body = ""
    try:
        raw = error.read(500)
    except OSError:
        raw = b""
    if raw:
        body = raw.decode("utf-8", errors="replace").strip()
        body = " ".join(body.split())
        if len(body) > 200:
            body = body[:200] + "…"
    location = error.headers.get("Location") if error.headers else None
    parts = [f"HTTP Error {error.code}: {error.reason}"]
    if location:
        parts.append(f"Location={location}")
    if body:
        parts.append(f"body={body!r}")
    return "; ".join(parts)


def wait_for_http_ok(
    url: str,
    *,
    timeout: float = 300.0,
    interval: float = 2.0,
    expected_status: int = 200,
    accept_status_codes: set[int] | None = None,
    follow_redirects: bool = False,
) -> int:
    """Block until *url* returns an accepted status or *timeout* seconds elapse.

    By default redirects are **not** followed: a 302/303 response is returned as
    that status (via ``HTTPError``) so ``accept_status_codes`` can include them.
    Pass ``follow_redirects=True`` for the stdlib opener behaviour.
    """
    allowed = accept_status_codes if accept_status_codes is not None else {expected_status}
    opener = urllib.request.urlopen if follow_redirects else _NO_REDIRECT_OPENER.open
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    last_detail = ""
    while time.monotonic() < deadline:
        try:
            with opener(url, timeout=min(interval, 10.0)) as response:
                if response.status in allowed:
                    return response.status
                last_error = RuntimeError(
                    f"unexpected HTTP status {response.status} for {url} "
                    f"(allowed: {sorted(allowed)})"
                )
                last_detail = str(last_error)
        except urllib.error.HTTPError as error:
            if error.code in allowed:
                return error.code
            last_error = error
            last_detail = _http_error_detail(error)
        except urllib.error.URLError as error:
            last_error = error.reason if isinstance(error.reason, BaseException) else error
            last_detail = str(last_error)
        except OSError as error:
            # Connection refused / reset while Odoo is still bootstrapping.
            last_error = error
            last_detail = str(error)
        time.sleep(interval)
    allowed_text = ", ".join(str(code) for code in sorted(allowed))
    message = f"Timed out after {timeout}s waiting for HTTP {{{allowed_text}}} from {url}"
    if last_detail:
        raise HttpWaitTimeoutError(f"{message}: {last_detail}") from last_error
    raise HttpWaitTimeoutError(message)
