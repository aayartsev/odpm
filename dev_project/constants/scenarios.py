DEVELOPER_SCENARIO = "developer"
SERVER_SCENARIO = "server"
CI_SCENARIO = "ci"
ODPM_SCENARIOS = {
    1: DEVELOPER_SCENARIO,
    2: SERVER_SCENARIO,
    3: CI_SCENARIO,
}
ODPM_SCENARIO_VALUES = frozenset(ODPM_SCENARIOS.values())
DEFAULT_ODPM_SCENARIO = DEVELOPER_SCENARIO

VENV_MODE_FRESH = "fresh"
VENV_MODE_BAKED = "baked"
VENV_MODE_VALUES = frozenset((VENV_MODE_FRESH, VENV_MODE_BAKED))

DEFAULT_ODPM_VERSION = "3.0"
# Manifest / manager compatibility line (`odpm.json` → `odpm_version`, `odpm --version`).
ODPM_VERSION = "4.0"
# Git tag and native package release line (deb/rpm); not the manifest contract version.
RELEASE_VERSION = "4.3-rc1"

RUN_MODE_ODOO = "odoo"
RUN_MODE_BOOTSTRAP_ONLY = "bootstrap_only"
RUN_MODE_VALUES = frozenset((RUN_MODE_ODOO, RUN_MODE_BOOTSTRAP_ONLY))
