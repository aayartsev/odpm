"""Reference compose fragment golden file for Mailpit service block."""

from __future__ import annotations

from dev_project.extensions.reference.mailpit import (
    MAILPIT_SERVICE_NAME,
    MAILPIT_SERVICE_SPEC,
)

MAILPIT_COMPOSE_FRAGMENT = f"""  {MAILPIT_SERVICE_NAME}:
    image: axllent/mailpit
    restart: unless-stopped
    ports:
      - 8025:8025
      - 1025:1025
"""

__all__ = ["MAILPIT_COMPOSE_FRAGMENT", "MAILPIT_SERVICE_NAME", "MAILPIT_SERVICE_SPEC"]
