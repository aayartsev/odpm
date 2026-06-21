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
# Single user-facing product version: CLI, pip/PyPI, deb/rpm, git tag (v{RELEASE_VERSION}).
RELEASE_VERSION = "4.4.3-beta"
# Recommended stable line for install docs and mike `stable` alias (bump on stable tag only).
LATEST_STABLE_RELEASE = "4.4.2"
# Alias for installed manager version (`odpm --version`, compat checks, new manifest defaults).
ODPM_VERSION = RELEASE_VERSION
# Flat odpm.json → odpm_version written for new projects (manifest contract v1).
MANIFEST_V1_CONTRACT_LINE = "4.0"
MANIFEST_SCHEMA_V1 = 1
MANIFEST_SCHEMA_V2 = 2
MANIFEST_SCHEMA_SUPPORTED_MAX = MANIFEST_SCHEMA_V2
SUPPORTED_V1_MANIFEST_CONTRACT_LINES = frozenset(
    {DEFAULT_ODPM_VERSION, MANIFEST_V1_CONTRACT_LINE}
)

RUN_MODE_ODOO = "odoo"
RUN_MODE_BOOTSTRAP_ONLY = "bootstrap_only"
RUN_MODE_VALUES = frozenset((RUN_MODE_ODOO, RUN_MODE_BOOTSTRAP_ONLY))
