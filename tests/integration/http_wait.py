"""Poll HTTP endpoints until success or timeout (golden-path E2E helper)."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request

_PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "no_proxy",
    "NO_PROXY",
    "all_proxy",
    "ALL_PROXY",
)
_RESPONSE_HEADER_NAMES = ("Server", "Via", "Content-Type")


class HttpWaitTimeoutError(TimeoutError):
    """Raised when an HTTP endpoint did not become ready in time."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Surface 3xx as ``HTTPError`` so callers can accept redirect statuses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


# Empty ProxyHandler replaces the default env proxy. urllib does not treat
# ``127.0.0.0/8`` in ``no_proxy`` as a match for ``127.0.0.1``, so a runner
# ``http_proxy`` would steal loopback readiness probes and return 403.
_NO_PROXY = urllib.request.ProxyHandler({})
_NO_REDIRECT_OPENER = urllib.request.build_opener(_NO_PROXY, _NoRedirectHandler)
_DIRECT_OPENER = urllib.request.build_opener(_NO_PROXY)


def _proxy_env_detail() -> str:
    """Show whether urllib might send the probe through an HTTP proxy."""
    parts = [
        f"{key}={os.environ[key]}"
        for key in _PROXY_ENV_KEYS
        if os.environ.get(key)
    ]
    shown = ", ".join(parts) if parts else "(none)"
    return f"proxy-env: {shown}"


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
    headers = error.headers
    location = headers.get("Location") if headers else None
    parts = [f"HTTP Error {error.code}: {error.reason}"]
    if headers:
        for name in _RESPONSE_HEADER_NAMES:
            value = headers.get(name)
            if value:
                parts.append(f"{name}={value}")
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
    Pass ``follow_redirects=True`` to follow redirects. Environment ``http_proxy``
    is ignored: this helper probes loopback services.
    """
    allowed = accept_status_codes if accept_status_codes is not None else {expected_status}
    opener = _DIRECT_OPENER.open if follow_redirects else _NO_REDIRECT_OPENER.open
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
    message = (
        f"Timed out after {timeout}s waiting for HTTP {{{allowed_text}}} from {url}"
        f" ({_proxy_env_detail()})"
    )
    if last_detail:
        raise HttpWaitTimeoutError(f"{message}: {last_detail}") from last_error
    raise HttpWaitTimeoutError(message)
