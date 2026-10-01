"""HTTP helpers for host-side downloads (stdlib urllib only)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, BinaryIO

from ..errors import ConfigError
from ..translations import _

DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 600.0
DEFAULT_LIST_TIMEOUT_SECONDS = 30.0
_PROGRESS_LOG_INTERVAL_SECONDS = 5.0

Transport = Callable[[urllib.request.Request, float], BinaryIO]
HeadersCallback = Callable[[Mapping[str, str]], None]
ProgressCallback = Callable[[int, int | None], None]


def _build_multipart_body(
    fields: Mapping[str, str],
) -> tuple[bytes, str]:
    boundary = f"----odpm{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            ).encode("ascii")
        )
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _progress_enabled(progress: bool | None) -> bool:
    if progress is None:
        return bool(sys.stderr.isatty())
    return bool(progress)


def _header_map(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", None)
    if headers is None:
        return {}
    try:
        return {str(k): str(v) for k, v in headers.items()}
    except Exception:
        return {}


def _content_length_from_headers(headers: Mapping[str, str]) -> int | None:
    raw = headers.get("Content-Length") or headers.get("content-length")
    if raw and str(raw).isdigit():
        return int(raw)
    return None


def _looks_like_html(sample: bytes) -> bool:
    lowered = sample.lstrip().lower()
    return lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html")


def _html_error_detail(sample: bytes) -> str:
    text = sample.decode("utf-8", errors="replace")
    for marker in (
        "Database backup error:",
        "AccessDenied",
        "Wrong master password",
        "is not known",
    ):
        idx = text.find(marker)
        if idx >= 0:
            snippet = text[idx : idx + 200].split("<", 1)[0].strip()
            if snippet:
                return snippet
    return text[:160].strip() or "HTML error page"


def _raise_html_backup_error(sample: bytes, url: str) -> None:
    detail = _html_error_detail(sample)
    raise ConfigError(
        _("HTTP backup failed for {URL}: {DETAIL}").format(URL=url, DETAIL=detail)
    )


def _write_with_progress(
    response: BinaryIO,
    dest: BinaryIO,
    *,
    progress: bool,
    content_length: int | None,
    on_progress: ProgressCallback | None,
    url: str,
) -> int:
    total = 0
    chunk_size = 64 * 1024
    last_report = -1
    last_callback_at = 0.0
    first_chunk = True
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        if first_chunk:
            first_chunk = False
            if _looks_like_html(chunk) and (
                content_length is None or content_length < 512 * 1024
            ):
                # Odoo often returns HTML 200 on auth/db errors.
                rest = chunk + response.read()
                _raise_html_backup_error(rest, url)
        dest.write(chunk)
        total += len(chunk)
        now = time.monotonic()
        if on_progress is not None and (
            total == content_length
            or now - last_callback_at >= _PROGRESS_LOG_INTERVAL_SECONDS
            or (content_length is None and total > 0 and last_callback_at == 0.0)
        ):
            on_progress(total, content_length)
            last_callback_at = now
        if progress and content_length and content_length > 0:
            pct = min(100, int(total * 100 / content_length))
            if pct != last_report and (pct % 5 == 0 or pct == 100):
                sys.stderr.write(f"\rdownload: {pct}%")
                sys.stderr.flush()
                last_report = pct
        elif progress and total != last_report and total % (1024 * 1024) < chunk_size:
            sys.stderr.write(f"\rdownload: {total // (1024 * 1024)} MiB")
            sys.stderr.flush()
            last_report = total
    if on_progress is not None and total > 0:
        on_progress(total, content_length)
    if progress:
        sys.stderr.write("\n")
        sys.stderr.flush()
    return total


def list_remote_odoo_databases(
    base_url: str,
    *,
    timeout: float = DEFAULT_LIST_TIMEOUT_SECONDS,
    transport: Transport | None = None,
) -> list[str]:
    """Return remote DB names via Odoo ``/web/database/list`` JSON-RPC."""
    url = str(base_url).strip().rstrip("/") + "/web/database/list"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {},
        "id": uuid.uuid4().hex,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        if transport is not None:
            response = transport(request, timeout)
            try:
                raw = response.read()
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
        else:
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                raise ConfigError(
                    _("Remote database list failed with status {STATUS} for {URL}").format(
                        STATUS=exc.code,
                        URL=url,
                    )
                ) from exc
            except urllib.error.URLError as exc:
                raise ConfigError(
                    _("Remote database list failed: {DETAIL}").format(DETAIL=exc.reason)
                ) from exc
    except ConfigError:
        raise
    except OSError as exc:
        raise ConfigError(
            _("Remote database list failed: {DETAIL}").format(DETAIL=exc)
        ) from exc

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(
            _("Remote database list returned invalid JSON from {URL}").format(URL=url)
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(
            _("Remote database list returned unexpected payload from {URL}").format(
                URL=url
            )
        )
    if data.get("error"):
        err = data["error"]
        detail = err if isinstance(err, str) else err.get("message") or err.get("data") or err
        raise ConfigError(
            _("Remote database list failed: {DETAIL}").format(DETAIL=detail)
        )
    result = data.get("result")
    if not isinstance(result, list):
        raise ConfigError(
            _("Remote database list returned unexpected payload from {URL}").format(
                URL=url
            )
        )
    return [str(item) for item in result]


def download_multipart_post(
    url: str,
    dest_path: str | Path,
    fields: Mapping[str, str],
    *,
    timeout: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    progress: bool | None = None,
    transport: Transport | None = None,
    on_response_headers: HeadersCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """POST multipart form fields and stream the response body to *dest_path*."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body, content_type = _build_multipart_body(fields)
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": content_type},
    )
    show_progress = _progress_enabled(progress)

    def _consume(response: BinaryIO) -> None:
        headers = _header_map(response)
        content_length = _content_length_from_headers(headers)
        ctype = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
        if "text/html" in ctype or "application/xhtml" in ctype:
            sample = response.read()
            if dest.exists():
                dest.unlink(missing_ok=True)
            _raise_html_backup_error(sample, url)
        if on_response_headers is not None:
            on_response_headers(headers)
        with dest.open("wb") as out:
            _write_with_progress(
                response,
                out,
                progress=show_progress,
                content_length=content_length,
                on_progress=on_progress,
                url=url,
            )

    try:
        if transport is not None:
            response = transport(request, timeout)
            try:
                _consume(response)
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
        else:
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    _consume(response)
            except urllib.error.HTTPError as exc:
                if dest.exists():
                    dest.unlink(missing_ok=True)
                raise ConfigError(
                    _("HTTP download failed with status {STATUS} for {URL}").format(
                        STATUS=exc.code,
                        URL=url,
                    )
                ) from exc
            except urllib.error.URLError as exc:
                if dest.exists():
                    dest.unlink(missing_ok=True)
                raise ConfigError(
                    _("HTTP download failed: {DETAIL}").format(DETAIL=exc.reason)
                ) from exc
    except ConfigError:
        raise
    except OSError as exc:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise ConfigError(
            _("HTTP download failed: {DETAIL}").format(DETAIL=exc)
        ) from exc
    return dest


def assert_odoo_backup_zip(path: str | Path) -> None:
    """Reject HTML error pages and non-zip payloads."""
    target = Path(path)
    if not target.is_file():
        raise ConfigError(
            _("Backup archive not found: {PATH}").format(PATH=target)
        )
    sample = target.read_bytes()[:512]
    if _looks_like_html(sample):
        raise ConfigError(
            _("Backup looks invalid (HTML response): {PATH}").format(PATH=target)
        )
    if not zipfile.is_zipfile(target):
        raise ConfigError(
            _("Backup looks invalid (not a zip archive): {PATH}").format(PATH=target)
        )


def safe_host_token(url: str) -> str:
    """Sanitize host from URL for archive filenames (script-compatible)."""
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname or parsed.netloc or "remote"
    host = host.split(":")[0]
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in host)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "remote"
