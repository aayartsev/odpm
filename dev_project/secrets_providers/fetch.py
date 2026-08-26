"""Orchestrate provider fetch → ``.odpm/secrets.json`` once per process."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .. import constants
from ..config.transforms.env_substitution import collect_secret_refs_in_value
from ..config.transforms.secret_refs import manifest_trees_for_secret_ref_gate
from ..errors import ConfigError
from ..host.cli.args import OdpmCliArgs
from ..logging import get_module_logger
from ..project_env.secrets import write_secrets_source
from ..translations import _
from .registry import get_secrets_provider
from .resolve import (
    dotenv_dict_from_user_env,
    load_provider_credentials,
    merge_environ_with_dotenv,
    resolve_secrets_provider_name,
)
from .session import SecretsFetchSession, session_for_config

_logger = get_module_logger(__name__)

FetchPhase = Literal["early", "prepare", "bake"]


@dataclass(frozen=True)
class SecretsFetchResult:
    did_fetch: bool
    provider_name: str
    key_count: int
    skipped: bool = False
    reason: str = ""


def _cli_args(value: object) -> OdpmCliArgs | None:
    return value if isinstance(value, OdpmCliArgs) else None


def _secret_refs_present(raw_manifest: Mapping[str, Any] | None, scenario: str) -> bool:
    if not isinstance(raw_manifest, dict):
        return False
    refs: set[str] = set()
    for tree in manifest_trees_for_secret_ref_gate(dict(raw_manifest), scenario):
        refs.update(collect_secret_refs_in_value(tree))
    return bool(refs)


def _provider_type_and_config(
    raw_manifest: Mapping[str, Any] | None,
    scenario: str,
) -> tuple[str | None, dict[str, Any], tuple[str, ...]]:
    if not isinstance(raw_manifest, dict):
        return None, {}, ()
    from ..manifest.scenario_overrides import resolve_effective_manifest_slice

    slice_ = resolve_effective_manifest_slice(dict(raw_manifest), scenario)
    spec = slice_.secrets
    if spec is None or spec.provider is None:
        return None, {}, spec.keys if spec is not None else ()
    mapping = spec.provider.as_mapping()
    mapping["keys"] = list(spec.keys)
    return spec.provider.type, mapping, spec.keys


def _should_fetch_early(
    provider_name: str,
    arguments: OdpmCliArgs | None,
    raw_manifest: Mapping[str, Any] | None,
    scenario: str,
) -> bool:
    if provider_name == constants.SECRETS_PROVIDER_FILE:
        return bool(arguments is not None and arguments.secrets_file)
    return _secret_refs_present(raw_manifest, scenario)


def ensure_secrets_source(
    *,
    project_dir: str,
    arguments: OdpmCliArgs | None,
    environ: Mapping[str, str],
    raw_manifest: Mapping[str, Any] | None,
    session: SecretsFetchSession,
    active_scenario: str,
    phase: FetchPhase = "prepare",
) -> SecretsFetchResult:
    """Fetch once per process. Early may skip; prepare/bake fetch remotes if needed."""
    if session.fetched:
        return SecretsFetchResult(
            did_fetch=False,
            provider_name=session.provider_name,
            key_count=session.key_count,
            skipped=False,
            reason="already fetched this run",
        )

    manifest_type, provider_config, _keys = _provider_type_and_config(
        raw_manifest, active_scenario
    )
    provider_name = resolve_secrets_provider_name(
        arguments, environ, manifest_type
    )

    if (
        provider_name == constants.SECRETS_PROVIDER_FILE
        and not (arguments is not None and arguments.secrets_file)
    ):
        return SecretsFetchResult(
            did_fetch=False,
            provider_name=provider_name,
            key_count=0,
            skipped=True,
            reason="file provider uses existing source",
        )

    if phase == "early" and not _should_fetch_early(
        provider_name, arguments, raw_manifest, active_scenario
    ):
        return SecretsFetchResult(
            did_fetch=False,
            provider_name=provider_name,
            key_count=0,
            skipped=True,
            reason="early fetch not required",
        )

    provider = get_secrets_provider(provider_name)
    credentials = load_provider_credentials(environ)
    secrets = provider.fetch(
        provider_config=provider_config,
        credentials=credentials,
        project_dir=project_dir,
        arguments=arguments,
    )
    write_secrets_source(project_dir, secrets)
    session.fetched = True
    session.provider_name = provider_name
    session.key_count = len(secrets)
    _logger.debug(
        "secrets fetch via %s: %s keys",
        provider_name,
        session.key_count,
    )
    return SecretsFetchResult(
        did_fetch=True,
        provider_name=provider_name,
        key_count=session.key_count,
        reason="fetched",
    )


def ensure_secrets_source_for_config(
    config: object,
    *,
    raw: Mapping[str, Any] | None,
    phase: FetchPhase,
) -> SecretsFetchResult:
    """Adapter for Config / MagicMock bootstrap objects."""
    session = session_for_config(config)
    arguments = _cli_args(getattr(config, "arguments", None))
    user_env = getattr(config, "user_env", None)
    scenario = str(getattr(user_env, "odpm_scenario", None) or "") or (
        constants.DEFAULT_ODPM_SCENARIO
    )
    environ = merge_environ_with_dotenv(
        os.environ,
        dotenv_dict_from_user_env(user_env),
    )
    project_dir = str(getattr(config, "project_dir", "") or "")
    if not project_dir:
        raise ConfigError(_("cannot fetch secrets: project directory is not set"))
    return ensure_secrets_source(
        project_dir=project_dir,
        arguments=arguments,
        environ=environ,
        raw_manifest=raw,
        session=session,
        active_scenario=scenario,
        phase=phase,
    )
