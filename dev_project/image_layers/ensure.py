"""Ensure layered CI images (ADR-027)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..errors import ConfigError, PipelineError
from ..host.cli import params as cli_params
from ..logging import get_module_logger
from ..project_env.image_build import ImageBuildSpec, get_ci_image_build_backend
from ..project_env.image_build.resolve import (
    resolve_ci_image_builder,
    resolve_ci_image_push,
)
from ..system_check_policy import environ_from_config
from ..translations import _
from .fingerprint import (
    compute_app_fingerprint,
    compute_deps_fingerprint,
    compute_lint_fingerprint,
    compute_platform_fingerprint,
    layer_image_ref,
)
from .registry import image_ref_exists

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs
    from ..project_env import CreateProjectEnvironment

_logger = get_module_logger(__name__)


def _program_dir(config: Config) -> str:
    return str(config.program_dir)


def _remote_target(args: OdpmCliArgs, config: Config) -> bool:
    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ)
    registry = os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    return bool(push or registry)


def _build_image(
    *,
    config: Config,
    args: OdpmCliArgs,
    context_dir: Path,
    dockerfile: Path,
    tag: str,
    push: bool,
) -> None:
    environ = environ_from_config(config)
    builder_name = resolve_ci_image_builder(args, environ=environ)
    spec = ImageBuildSpec(
        context_dir=str(context_dir),
        dockerfile=str(dockerfile),
        tag=tag,
        platform=f"linux/{config.arch}",
        push=push,
        project_dir=config.project_dir,
    )
    get_ci_image_build_backend(builder_name).build(spec)


def _copy_template(program_dir: str, name: str, dest: Path) -> None:
    src = Path(program_dir) / "dev_project" / "templates" / name
    if not src.is_file():
        raise ConfigError(
            _("missing layered image template {NAME}").format(NAME=name)
        )
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def ensure_base(project_env: CreateProjectEnvironment) -> str:
    from ..project_env.base_image import BaseImageBuilder
    from ..project_env.services import BaseImageService

    BaseImageService(project_env).ensure_base_image()
    return BaseImageBuilder(project_env).resolve_base_image_ref()


def ensure_platform(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
) -> str:
    config = project_env.config
    program_dir = _program_dir(config)
    fp = compute_platform_fingerprint(config, program_dir=program_dir)
    ref = layer_image_ref(config, layer="platform", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(ref, remote=remote):
        _logger.info("image platform ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image platform ensure: miss — building %s", ref)
    base_ref = ensure_base(project_env)
    from ..project_env.ci_image import CiImageBuilder

    builder = CiImageBuilder(project_env)
    builder.prepare_ci_build_context()
    full_ctx = Path(config.ci_build_context_dir)
    context_dir = Path(config.project_dir) / ".odpm" / "platform-build-context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    for name in ("odoo", "dev_project", "ci"):
        src = full_ctx / name
        if not src.exists():
            raise PipelineError(
                _("platform context missing {PATH}").format(PATH=src),
                exit_code=1,
            )
        shutil.copytree(src, context_dir / name, dirs_exist_ok=True)
    dockerfile = context_dir / "Dockerfile.platform"
    _copy_template(program_dir, "dockerfile_platform", dockerfile)
    text = dockerfile.read_text(encoding="utf-8")
    text = text.replace(
        "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}", f"FROM {base_ref}"
    )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir,
        "dockerignore_platform",
        context_dir / ".dockerignore",
    )
    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ) or remote
    _build_image(
        config=config,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image platform ensure: done %s", ref)
    return ref


def ensure_deps(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
) -> str | None:
    config = project_env.config
    program_dir = _program_dir(config)
    parent = platform_ref or args.image_from
    if not parent:
        parent = ensure_platform(project_env, args)
    fp = compute_deps_fingerprint(
        config, program_dir=program_dir, platform_ref=parent
    )
    if fp is None:
        _logger.info("image deps ensure: no dependencies — layer skipped")
        return None
    ref = layer_image_ref(config, layer="deps", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(ref, remote=remote):
        _logger.info("image deps ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image deps ensure: miss — building %s", ref)
    from ..project_env.ci_image import CiImageBuilder

    builder = CiImageBuilder(project_env)
    builder.prepare_ci_build_context()
    full_ctx = Path(config.ci_build_context_dir)
    addons_src = full_ctx / "extra-addons"
    if not addons_src.is_dir():
        _logger.info(
            "image deps ensure: no extra-addons in context — treating as noop"
        )
        return None
    context_dir = Path(config.project_dir) / ".odpm" / "deps-build-context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    shutil.copytree(addons_src, context_dir / "extra-addons")
    dockerfile = context_dir / "Dockerfile.deps"
    _copy_template(program_dir, "dockerfile_deps", dockerfile)
    text = dockerfile.read_text(encoding="utf-8")
    text = text.replace(
        "ARG PLATFORM_IMAGE\nFROM ${PLATFORM_IMAGE}", f"FROM {parent}"
    )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_deps", context_dir / ".dockerignore"
    )
    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ) or remote
    _build_image(
        config=config,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image deps ensure: done %s", ref)
    return ref


def _developing_git_sha(config: Config) -> str:
    developing = getattr(config.bootstrap, "developing_project", None)
    path = None
    if developing is not None:
        path = getattr(developing, "path", None) or getattr(
            developing, "project_path", None
        )
    if not path:
        # Fallback: common developing checkout location
        candidate = Path(config.project_dir) / "extra-addons"
        # Prefer explicit git at project developing link
        path = config.project_dir
    root = Path(str(path))
    if not (root / ".git").exists():
        # try nested developing folder names used by odpm
        for name in ("developing", "aktta"):
            alt = Path(config.project_dir) / name
            if (alt / ".git").is_dir():
                root = alt
                break
    if not (root / ".git").exists():
        raise ConfigError(
            _(
                "developing project must be a git repository for image app "
                "ensure (git rev-parse HEAD)"
            )
        )
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ConfigError(
            _("git rev-parse HEAD failed in {PATH}: {ERR}").format(
                PATH=root, ERR=(completed.stderr or "").strip()
            )
        )
    return (completed.stdout or "").strip()


def ensure_app(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    parent_ref: str | None = None,
) -> str:
    config = project_env.config
    program_dir = _program_dir(config)
    developing_sha = _developing_git_sha(config)
    parent = parent_ref or args.image_from
    if not parent:
        deps_ref = ensure_deps(project_env, args)
        parent = deps_ref or ensure_platform(project_env, args)

    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ)
    tag = args.image_tag or config.odoo_ci_image_name
    remote = bool(push) or bool(
        os.environ.get("ODPM_BASE_IMAGE_REGISTRY")
        or os.environ.get("CI_REGISTRY_IMAGE")
    )
    secrets_baked = bool(
        os.environ.get("ODPM_BAKE_SECRETS", "").strip()
        in {"1", "true", "True", "yes", "YES"}
    )
    app_fp = compute_app_fingerprint(
        config,
        program_dir=program_dir,
        parent_ref=parent,
        developing_git_sha=developing_sha,
        secrets_baked=secrets_baked,
    )
    cache_ref = layer_image_ref(config, layer="app", fingerprint=app_fp)
    if image_ref_exists(cache_ref, remote=remote):
        _logger.info("image app ensure: skip (exists) %s", cache_ref)
        return tag or cache_ref

    _logger.info(
        "image app ensure: miss — building %s (cache %s) FROM %s",
        tag,
        cache_ref,
        parent,
    )
    from ..project_env.ci_image import CiImageBuilder

    builder = CiImageBuilder(project_env)
    builder.prepare_ci_build_context()
    # Drop odoo/.venv from context for thin app (already in parent).
    full_ctx = Path(config.ci_build_context_dir)
    for drop in ("odoo", ".venv"):
        target = full_ctx / drop
        if target.exists():
            shutil.rmtree(target)
    dockerfile = full_ctx / "Dockerfile.app"
    _copy_template(program_dir, "dockerfile_app", dockerfile)
    text = dockerfile.read_text(encoding="utf-8")
    text = text.replace(
        "ARG PLATFORM_IMAGE\nFROM ${PLATFORM_IMAGE}", f"FROM {parent}"
    )
    secrets_src = full_ctx / "runtime" / "secrets.json"
    if secrets_src.is_file():
        text = text.replace(
            "# Optional secrets — enabled when secrets file is present in context:\n"
            "#COPY --chown=odoo:odoo runtime/secrets.json /run/odpm/secrets.json\n"
            "#ENV ODPM_SECRETS_PATH=/run/odpm/secrets.json\n",
            f"COPY --chown={constants.CONTAINER_USER}:{constants.CONTAINER_USER} "
            f"runtime/secrets.json {constants.ODPM_SECRETS_CONTAINER_PATH}\n"
            f"ENV {constants.ODPM_SECRETS_PATH_ENV}="
            f"{constants.ODPM_SECRETS_CONTAINER_PATH}\n",
        )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_app", full_ctx / ".dockerignore"
    )
    build_tag = tag or cache_ref
    _build_image(
        config=config,
        args=args,
        context_dir=full_ctx,
        dockerfile=dockerfile,
        tag=build_tag,
        push=push,
    )
    if tag and tag != cache_ref and not remote:
        # Retag local cache alias for fingerprint-based hits next run.
        docker = shutil.which("docker")
        if docker:
            subprocess.run(
                [docker, "tag", build_tag, cache_ref],
                check=False,
                capture_output=True,
                text=True,
            )
    _logger.info("image app ensure: done %s", build_tag)
    return build_tag


def ensure_lint(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
) -> str:
    config = project_env.config
    program_dir = _program_dir(config)
    pre_commit = Path(config.project_dir) / ".pre-commit-config.yaml"
    if not pre_commit.is_file():
        raise ConfigError(
            _(
                "image lint ensure requires .pre-commit-config.yaml in the "
                "project root after sources prepare"
            )
        )
    platform_fp = compute_platform_fingerprint(config, program_dir=program_dir)
    parent = platform_ref or args.image_from or ensure_platform(project_env, args)
    fp = compute_lint_fingerprint(
        config, program_dir=program_dir, platform_fp=platform_fp
    )
    ref = layer_image_ref(config, layer="lint", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(ref, remote=remote):
        _logger.info("image lint ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image lint ensure: miss — building %s", ref)
    context_dir = Path(config.project_dir) / ".odpm" / "lint-build-context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    shutil.copy2(pre_commit, context_dir / ".pre-commit-config.yaml")
    hooks = Path(config.project_dir) / ".pre-commit-hooks.yaml"
    if hooks.is_file():
        shutil.copy2(hooks, context_dir / ".pre-commit-hooks.yaml")
    dockerfile = context_dir / "Dockerfile.lint"
    _copy_template(program_dir, "dockerfile_lint", dockerfile)
    text = dockerfile.read_text(encoding="utf-8")
    text = text.replace(
        "ARG PLATFORM_IMAGE\nFROM ${PLATFORM_IMAGE}", f"FROM {parent}"
    )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_lint", context_dir / ".dockerignore"
    )
    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ) or remote
    _build_image(
        config=config,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image lint ensure: done %s", ref)
    return ref


def ensure_image_layer(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
) -> str | None:
    layer = args.image_layer
    if layer == cli_params.IMAGE_BASE_LAYER:
        return ensure_base(project_env)
    if layer == cli_params.IMAGE_PLATFORM_LAYER:
        return ensure_platform(project_env, args)
    if layer == cli_params.IMAGE_DEPS_LAYER:
        return ensure_deps(project_env, args)
    if layer == cli_params.IMAGE_APP_LAYER:
        return ensure_app(project_env, args)
    if layer == cli_params.IMAGE_LINT_LAYER:
        return ensure_lint(project_env, args)
    raise ConfigError(
        _("unknown image layer {LAYER}").format(LAYER=layer)
    )


def run_layered_build(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
) -> str:
    """Shortcut used by ``odpm build``: base → platform → deps? → app."""
    ensure_base(project_env)
    platform_ref = ensure_platform(project_env, args)
    deps_ref = ensure_deps(project_env, args, platform_ref=platform_ref)
    return ensure_app(
        project_env, args, parent_ref=deps_ref or platform_ref
    )
