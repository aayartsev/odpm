"""Host plan message localization (build-time gettext)."""

from __future__ import annotations

from ..translations import _


def plan_msg(msgid: str, /, **kwargs: object) -> str:
    """Translate a plan description/reason/warning msgid at plan build time."""
    if kwargs:
        return _(msgid).format(**kwargs)
    return _(msgid)
