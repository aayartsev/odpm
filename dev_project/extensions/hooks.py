"""Manifest lifecycle hooks (shell argv and pluggy hook runners)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ..errors import ConfigError, PipelineError
from ..logging import get_module_logger
from ..subprocess_runner import run_or_raise
from ..translations import _

if TYPE_CHECKING:
    from ..config.transforms.env_substitution import EnvResolver
    from .context import ExtensionHostContext

_logger = get_module_logger(__name__)

LifecyclePhase = Literal["post_clone", "post_prepare", "pre_up"]
LIFECYCLE_PHASES: tuple[LifecyclePhase, ...] = (
    "post_clone",
    "post_prepare",
    "pre_up",
)


def parse_hook_phase(
    manifest_hooks: dict[str, Any] | None,
    phase: LifecyclePhase,
) -> tuple[tuple[tuple[str, ...], ...], tuple[str, ...]]:
    """Split manifest hook entries into shell argv tuples and plugin ids."""
    if not isinstance(manifest_hooks, dict):
        return (), ()
    entries = manifest_hooks.get(phase)
    if not isinstance(entries, list):
        return (), ()
    shell_commands: list[tuple[str, ...]] = []
    plugin_ids: list[str] = []
    for entry in entries:
        if isinstance(entry, list):
            if not entry:
                raise ConfigError(
                    _("Invalid manifest hook {PHASE}: empty command").format(PHASE=phase)
                )
            shell_commands.append(tuple(str(item) for item in entry))
            continue
        if isinstance(entry, str):
            plugin_id = entry.strip()
            if not plugin_id:
                raise ConfigError(
                    _("Invalid manifest hook {PHASE}: empty plugin id").format(
                        PHASE=phase
                    )
                )
            plugin_ids.append(plugin_id)
            continue
        raise ConfigError(
            _("Invalid manifest hook {PHASE}: expected command argv or plugin id").format(
                PHASE=phase
            )
        )
    return tuple(shell_commands), tuple(plugin_ids)


def _expand_hook_argv(
    argv: tuple[str, ...],
    *,
    resolver: EnvResolver,
    phase: LifecyclePhase,
    command_index: int,
) -> tuple[str, ...]:
    from ..config.transforms.env_substitution import expand_env_string

    return tuple(
        expand_env_string(
            item,
            resolver,
            field_path=f"hooks.{phase}[{command_index}][]",
        )
        for item in argv
    )


def run_lifecycle_hooks(
    ext: ExtensionHostContext,
    phase: LifecyclePhase,
    *,
    cwd: str,
    env_resolver: EnvResolver | None = None,
) -> None:
    """Run manifest shell hooks and registered pluggy hook runners for *phase*."""
    from .registry import get_hook_runner, load_hook_runners

    load_hook_runners()
    shell_commands, plugin_ids = parse_hook_phase(ext.manifest_hooks, phase)
    subprocess_env = None
    if env_resolver is not None:
        from ..config.transforms.env_substitution import merged_subprocess_environ

        subprocess_env = merged_subprocess_environ(env_resolver)
    for command_index, argv in enumerate(shell_commands):
        if env_resolver is not None:
            argv = _expand_hook_argv(
                argv,
                resolver=env_resolver,
                phase=phase,
                command_index=command_index,
            )
        command = " ".join(argv)
        _logger.info("Running manifest hook %s: %s", phase, command)
        try:
            if subprocess_env is not None:
                run_or_raise(argv, cwd=cwd, env=subprocess_env)
            else:
                run_or_raise(argv, cwd=cwd)
        except Exception as exc:
            message = _("Manifest hook {PHASE} failed: {COMMAND}").format(
                PHASE=phase,
                COMMAND=command,
            )
            _logger.error("%s: %s", message, exc)
            exit_code = getattr(exc, "exit_code", 1)
            raise PipelineError(message, exit_code=exit_code) from exc
    for plugin_id in plugin_ids:
        runner = get_hook_runner(plugin_id)
        if runner is None:
            raise ConfigError(
                _("Unknown manifest hook plugin id: {PLUGIN_ID}").format(
                    PLUGIN_ID=plugin_id
                )
            )
        _logger.info("Running hook plugin %s (%s)", plugin_id, phase)
        if phase == "post_clone":
            _run_hook_runner_phase(runner, "run_post_clone", ext)
        elif phase == "post_prepare":
            runner.run_post_prepare(ext)
        else:
            runner.run_pre_up(ext)


def _run_hook_runner_phase(runner: object, method_name: str, ext: ExtensionHostContext) -> None:
    method = getattr(runner, method_name, None)
    if method is None:
        raise ConfigError(
            _("Hook plugin {PLUGIN_ID} does not implement {METHOD}").format(
                PLUGIN_ID=getattr(runner, "name", runner),
                METHOD=method_name,
            )
        )
    method(ext)
