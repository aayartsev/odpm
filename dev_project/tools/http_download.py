"""HTTP helpers for host-side downloads (stdlib urllib only)."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import BinaryIO

from ..errors import ConfigError
from ..translations import _

DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 600.0

Transport = Callable[[urllib.request.Request, float], BinaryIO]


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


def _write_with_progress(
    response: BinaryIO,
    dest: BinaryIO,
    *,
    progress: bool,
    content_length: int | None,
) -> int:
    total = 0
    chunk_size = 64 * 1024
    last_report = -1
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        dest.write(chunk)
        total += len(chunk)
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
    if progress:
        sys.stderr.write("\n")
        sys.stderr.flush()
    return total


def download_multipart_post(
    url: str,
    dest_path: str | Path,
    fields: Mapping[str, str],
    *,
    timeout: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    progress: bool | None = None,
    transport: Transport | None = None,
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
    try:
        if transport is not None:
            response = transport(request, timeout)
            try:
                with dest.open("wb") as out:
                    _write_with_progress(
                        response,
                        out,
                        progress=show_progress,
                        content_length=None,
                    )
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
        else:
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    length_hdr = response.headers.get("Content-Length")
                    content_length: int | None = None
                    if length_hdr and str(length_hdr).isdigit():
                        content_length = int(length_hdr)
                    with dest.open("wb") as out:
                        _write_with_progress(
                            response,
                            out,
                            progress=show_progress,
                            content_length=content_length,
                        )
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
    lowered = sample.lstrip().lower()
    if lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
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
