#!/usr/bin/env bash
# Run the unit tests that historically failed on Python 3.10 CI (mock.patch + locale).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGETS=(
  tests.test_host_config.ConfigBootstrapContextWiringTests.test_bootstrap_context_rewrite_odpm_json_delegates_to_writer
  tests.test_odpm_locale_env.InteractiveLocaleWizardTests.test_interactive_env_file_includes_locale
  tests.test_user_env_debugger.UserEnvDebuggerTests.test_interactive_env_includes_debugger_keys
  tests.test_user_env_debugger.UserEnvDebuggerTests.test_interactive_pydevd_connect_prompts_connect_host_and_suspend
)

echo "Python 3.10 CI target tests (${#TARGETS[@]})..."

if command -v python3.10 >/dev/null 2>&1; then
  python3.10 -m unittest "${TARGETS[@]}" -v
else
  # Quote targets so the whole unittest invocation runs inside the container.
  quoted_targets=""
  for target in "${TARGETS[@]}"; do
    quoted_targets+=" ${target@Q}"
  done
  docker run --rm -v "$ROOT:/src" -w /src python:3.10-slim bash -lc \
    "pip install -q -e '.[test]' && python -m unittest${quoted_targets} -v"
fi
