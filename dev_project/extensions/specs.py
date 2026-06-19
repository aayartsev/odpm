"""Extension hook specifications (pluggy markers)."""

from __future__ import annotations

import pluggy

PROJECT_NAME = "odpm"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


class OdpmExtensionSpecs:
    """Host extension hooks for prepare steps and future lifecycle hooks."""

    @hookspec
    def odpm_prepare_steps(self):
        """Return :class:`PrepareStepPlugin`, :class:`PrepareStepDef`, or a sequence."""
