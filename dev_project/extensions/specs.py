"""Extension hook specifications (pluggy markers)."""

from __future__ import annotations

import pluggy

PROJECT_NAME = "odpm"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


class OdpmExtensionSpecs:
    """Host extension hooks for prepare steps and lifecycle hook runners."""

    @hookspec
    def odpm_prepare_steps(self):
        """Return :class:`PrepareStepPlugin`, :class:`PrepareStepDef`, or a sequence."""

    @hookspec
    def odpm_hook_runners(self):
        """Return :class:`HookRunner` plugins or a sequence."""
