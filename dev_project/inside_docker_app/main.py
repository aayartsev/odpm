"""Deprecated entrypoint alias. Prefer ``dev_project.inside_docker_app.run_odoo``."""

from __future__ import annotations

import warnings

warnings.warn(
    "dev_project.inside_docker_app.main is deprecated; "
    "use python3 -m dev_project.inside_docker_app.run_odoo with ODPM_CONFIG_PATH",
    DeprecationWarning,
    stacklevel=1,
)

from .run_odoo import main

if __name__ == "__main__":
    main()
