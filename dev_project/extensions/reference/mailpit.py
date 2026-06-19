"""Reference Mailpit compose service for manifest v2 ``services``."""

from __future__ import annotations

MAILPIT_SERVICE_NAME = "mailpit"

MAILPIT_SERVICE_SPEC: dict[str, object] = {
    "image": "axllent/mailpit",
    "restart": "unless-stopped",
    "ports": ["8025:8025", "1025:1025"],
}
