"""Deprecation warnings for backward-compatible root shims."""

from __future__ import annotations

import warnings


def warn_shim_deprecated(module_name: str, canonical: str) -> None:
    warnings.warn(
        f"{module_name} is deprecated; use {canonical} instead.",
        DeprecationWarning,
        stacklevel=3,
    )
