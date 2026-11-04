"""Ensure layered CI images (ADR-027)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

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
from .registry import (
    force_rebuild_requested,
    image_ref_exists,
    retag_image,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs
    from ..project_env import CreateProjectEnvironment

_logger = get_module_logger(__name__)


def _program_dir(config: Config) -> str:
    return str(config.program_dir)


def _remote_target(args: OdpmCliArgs, config: Config) -> bool:
    """Whether presence checks should use the remote registry (crane).

    Registry env alone is enough to *probe* remote hits; it does **not**
    imply a push (see :func:`_want_push`).
    """
    environ = environ_from_config(config)
    push = resolve_ci_image_push(args, environ=environ)
    registry = os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    return bool(push or registry)


def _want_push(args: OdpmCliArgs, config: Config) -> bool:
    """Explicit push only (``--image-push`` / ``ODPM_CI_IMAGE_PUSH``)."""
    return bool(
        resolve_ci_image_push(args, environ=environ_from_config(config))
    )


def _force_this_layer(force: bool | None) -> bool:
    if force is not None:
        return force
    return force_rebuild_requested()


def _docker_push_or_raise(ref: str) -> None:
    docker = shutil.which("docker")
    if not docker:
        raise ConfigError(
            _("docker is required to push layered CI image {REF}").format(
                REF=ref
            )
        )
    completed = subprocess.run(
        [docker, "push", ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ConfigError(
            _("docker push failed for {REF}: {ERR}").format(
                REF=ref,
                ERR=(completed.stderr or completed.stdout or "").strip(),
            )
        )
    _logger.info("pushed local image %s", ref)


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


def _rewrite_from_line(text: str, *, arg_name: str, image_ref: str) -> str:
    """Replace ``ARG X`` + ``FROM ${X}`` with a concrete ``FROM`` line."""
    needle = f"ARG {arg_name}\nFROM ${{{arg_name}}}"
    if needle not in text:
        raise ConfigError(
            _(
                "layered Dockerfile missing expected FROM stub "
                "ARG {ARG} / FROM ${{{ARG}}}"
            ).format(ARG=arg_name)
        )
    return text.replace(needle, f"FROM {image_ref}", 1)


def developing_project_path(config: Config) -> Path | None:
    """Resolve the developing checkout path when available."""
    developing = getattr(config, "developing_project", None)
    if developing is None:
        bootstrap = getattr(config, "bootstrap", None)
        developing = (
            getattr(bootstrap, "developing_project", None)
            if bootstrap is not None
            else None
        )
    if developing is None:
        return None
    if isinstance(developing, str) and developing.strip():
        # Unresolved link string — not a filesystem path.
        return None
    path = getattr(developing, "project_path", None) or getattr(
        developing, "path", None
    )
    if not path:
        return None
    return Path(str(path)).resolve()


def _developing_git_sha(config: Config) -> str:
    root = developing_project_path(config)
    if root is None or not (root / ".git").exists():
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


def _copy_deps_extra_addons(
    project_env: CreateProjectEnvironment,
    *,
    full_ctx: Path,
    dest_addons: Path,
) -> int:
    """Copy dependency trees into deps context, excluding developing."""
    config = project_env.config
    developing = developing_project_path(config)
    src_root = full_ctx / "extra-addons"
    if not src_root.is_dir():
        return 0
    dest_addons.mkdir(parents=True, exist_ok=True)
    copied = 0
    # Prefer mapped_folders so we skip by absolute developing path.
    mapped = list(getattr(project_env, "mapped_folders", None) or [])
    docker_extra = str(getattr(config, "docker_extra_addons", "") or "")
    used_mapped = False
    for item in mapped:
        local = getattr(item, "local", None)
        docker = str(getattr(item, "docker", "") or "")
        if not local or not docker_extra:
            continue
        if docker != docker_extra and not docker.startswith(f"{docker_extra}/"):
            continue
        if docker == docker_extra:
            continue
        local_path = Path(str(local)).resolve()
        if developing is not None and local_path == developing:
            _logger.info(
                "image deps ensure: skipping developing tree %s", local_path
            )
            continue
        rel = Path(docker).relative_to(Path(docker_extra))
        dest = dest_addons / rel
        if local_path.is_dir():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(local_path, dest, dirs_exist_ok=True)
            copied += 1
            used_mapped = True
    if used_mapped:
        return copied
    # Fallback: copy context children, skipping only path-identical developing
    # (never basename-only — avoids dropping OCA trees with the same folder name).
    for child in sorted(src_root.iterdir()):
        if developing is not None:
            try:
                if child.resolve() == developing:
                    _logger.info(
                        "image deps ensure: skipping developing path %s",
                        child,
                    )
                    continue
            except OSError:
                pass
        if child.is_dir():
            shutil.copytree(child, dest_addons / child.name, dirs_exist_ok=True)
            copied += 1
        elif child.is_file():
            shutil.copy2(child, dest_addons / child.name)
            copied += 1
    return copied


def _publish_alias(
    *,
    cache_ref: str,
    publish_tag: str | None,
    push: bool,
) -> None:
    """Alias fingerprint cache ref as the publish tag.

    Without ``push``, only a local ``docker tag`` is attempted (and skipped
    quietly when the cache image is not local). With ``push``, prefer
    ``crane copy`` (required when the cache image is not local — typical
    after Kaniko). Fall back to ``docker tag`` + ``docker push`` only when
    the cache ref exists in the local daemon.
    """
    if not publish_tag or publish_tag == cache_ref:
        return
    if push:
        crane = shutil.which("crane")
        if crane:
            retag_image(cache_ref, publish_tag, remote=True)
            return
        if image_ref_exists(cache_ref, remote=False, force=False):
            retag_image(cache_ref, publish_tag, remote=False)
            _docker_push_or_raise(publish_tag)
            return
        raise ConfigError(
            _(
                "crane is required to publish layered CI image alias "
                "({SRC} → {DST}) when the cache image is not available "
                "locally (typical after kaniko builds)"
            ).format(SRC=cache_ref, DST=publish_tag)
        )
    if not image_ref_exists(cache_ref, remote=False, force=False):
        _logger.info(
            "image app ensure: skip local publish alias %s "
            "(cache %s not present locally; use --image-push to publish)",
            publish_tag,
            cache_ref,
        )
        return
    retag_image(cache_ref, publish_tag, remote=False)


def ensure_base(
    project_env: CreateProjectEnvironment,
    *,
    force: bool | None = None,
) -> str:
    from ..project_env.base_image import BaseImageBuilder
    from ..project_env.base_image_identity import (
        base_image_identity_path,
        expected_base_image_identity,
        write_base_image_identity,
    )
    from ..project_env.services import BaseImageService

    builder = BaseImageBuilder(project_env)
    if _force_this_layer(force):
        stamp = Path(base_image_identity_path(project_env.config.project_dir))
        if stamp.is_file():
            stamp.unlink()
            _logger.info(
                "ODPM_IMAGE_FORCE_REBUILD: removed base identity stamp %s",
                stamp,
            )
        _logger.info("image base ensure: force rebuild")
        image_ref = builder.resolve_base_image_ref()
        builder.build_base_image()
        write_base_image_identity(
            project_env.config.project_dir,
            expected_base_image_identity(
                project_env.config, image_ref=image_ref
            ),
        )
        return image_ref
    BaseImageService(project_env).ensure_base_image()
    return builder.resolve_base_image_ref()


def ensure_platform(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    force: bool | None = None,
) -> str:
    config = project_env.config
    program_dir = _program_dir(config)
    fp = compute_platform_fingerprint(config, program_dir=program_dir)
    ref = layer_image_ref(config, layer="platform", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image platform ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image platform ensure: miss — building %s", ref)
    # Parent base ensure never inherits FORCE for this layer.
    base_ref = ensure_base(project_env, force=False)
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
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="BASE_IMAGE",
        image_ref=base_ref,
    )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir,
        "dockerignore_platform",
        context_dir / ".dockerignore",
    )
    push = _want_push(args, config)
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
    force: bool | None = None,
) -> str | None:
    config = project_env.config
    program_dir = _program_dir(config)
    parent = platform_ref or args.image_from
    if not parent:
        # Parent ensure never inherits FORCE for this layer.
        parent = ensure_platform(project_env, args, force=False)
    fp = compute_deps_fingerprint(
        config, program_dir=program_dir, platform_ref=parent
    )
    if fp is None:
        _logger.info("image deps ensure: no dependencies — layer skipped")
        return None
    ref = layer_image_ref(config, layer="deps", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image deps ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image deps ensure: miss — building %s", ref)
    from ..project_env.ci_image import CiImageBuilder

    builder = CiImageBuilder(project_env)
    builder.prepare_ci_build_context()
    full_ctx = Path(config.ci_build_context_dir)
    context_dir = Path(config.project_dir) / ".odpm" / "deps-build-context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    copied = _copy_deps_extra_addons(
        project_env,
        full_ctx=full_ctx,
        dest_addons=context_dir / "extra-addons",
    )
    if copied == 0:
        raise ConfigError(
            _(
                "image deps ensure: dependencies are declared in the lock but "
                "no dependency trees remain after excluding developing; "
                "run prepare --stop-after sources first"
            )
        )
    dockerfile = context_dir / "Dockerfile.deps"
    _copy_template(program_dir, "dockerfile_deps", dockerfile)
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
    )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_deps", context_dir / ".dockerignore"
    )
    push = _want_push(args, config)
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


def ensure_app(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    parent_ref: str | None = None,
    force: bool | None = None,
) -> str:
    config = project_env.config
    program_dir = _program_dir(config)
    developing_sha = _developing_git_sha(config)
    parent = parent_ref or args.image_from
    if not parent:
        deps_ref = ensure_deps(project_env, args, force=False)
        parent = deps_ref or ensure_platform(project_env, args, force=False)

    push = _want_push(args, config)
    publish_tag = args.image_tag or config.odoo_ci_image_name
    remote = _remote_target(args, config)
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
    force_this = _force_this_layer(force)
    if image_ref_exists(cache_ref, remote=remote, force=force_this):
        _logger.info("image app ensure: skip (exists) %s", cache_ref)
        _publish_alias(
            cache_ref=cache_ref,
            publish_tag=publish_tag,
            push=push,
        )
        return publish_tag or cache_ref

    _logger.info(
        "image app ensure: miss — building cache %s (publish %s) FROM %s",
        cache_ref,
        publish_tag,
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
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
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
    # Push only when explicitly requested; registry env alone is for presence.
    _build_image(
        config=config,
        args=args,
        context_dir=full_ctx,
        dockerfile=dockerfile,
        tag=cache_ref,
        push=push,
    )
    _publish_alias(
        cache_ref=cache_ref,
        publish_tag=publish_tag,
        push=push,
    )
    _logger.info(
        "image app ensure: done cache=%s publish=%s",
        cache_ref,
        publish_tag or cache_ref,
    )
    return publish_tag or cache_ref


def ensure_lint(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
    force: bool | None = None,
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
    parent = platform_ref or args.image_from
    if not parent:
        parent = ensure_platform(project_env, args, force=False)
    fp = compute_lint_fingerprint(
        config, program_dir=program_dir, platform_fp=platform_fp
    )
    ref = layer_image_ref(config, layer="lint", fingerprint=fp)
    remote = _remote_target(args, config)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image lint ensure: skip (exists) %s", ref)
        return ref

    _logger.info("image lint ensure: miss — building %s", ref)
    context_dir = Path(config.project_dir) / ".odpm" / "lint-build-context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    shutil.copy2(pre_commit, context_dir / ".pre-commit-config.yaml")
    hooks = Path(config.project_dir) / ".pre-commit-hooks.yaml"
    has_hooks = hooks.is_file()
    if has_hooks:
        shutil.copy2(hooks, context_dir / ".pre-commit-hooks.yaml")
    dockerfile = context_dir / "Dockerfile.lint"
    _copy_template(program_dir, "dockerfile_lint", dockerfile)
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
    )
    if has_hooks:
        text = text.replace(
            "COPY --chown=${CONTAINER_USER}:${CONTAINER_USER} "
            ".pre-commit-config.yaml .pre-commit-config.yaml\n",
            "COPY --chown=${CONTAINER_USER}:${CONTAINER_USER} "
            ".pre-commit-config.yaml .pre-commit-config.yaml\n"
            "COPY --chown=${CONTAINER_USER}:${CONTAINER_USER} "
            ".pre-commit-hooks.yaml .pre-commit-hooks.yaml\n",
        )
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_lint", context_dir / ".dockerignore"
    )
    push = _want_push(args, config)
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
    # Top-level ensure: FORCE applies only to this layer.
    force = force_rebuild_requested()
    if layer == cli_params.IMAGE_BASE_LAYER:
        return ensure_base(project_env, force=force)
    if layer == cli_params.IMAGE_PLATFORM_LAYER:
        return ensure_platform(project_env, args, force=force)
    if layer == cli_params.IMAGE_DEPS_LAYER:
        return ensure_deps(project_env, args, force=force)
    if layer == cli_params.IMAGE_APP_LAYER:
        return ensure_app(project_env, args, force=force)
    if layer == cli_params.IMAGE_LINT_LAYER:
        return ensure_lint(project_env, args, force=force)
    raise ConfigError(
        _("unknown image layer {LAYER}").format(LAYER=layer)
    )


def run_layered_build(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
) -> str:
    """Shortcut used by ``odpm build``: base → platform → deps? → app.

    ``ODPM_IMAGE_FORCE_REBUILD`` forces only the **app** layer here so parents
    are not rebuilt «along with» the final image (ADR-027).
    """
    ensure_base(project_env, force=False)
    platform_ref = ensure_platform(project_env, args, force=False)
    deps_ref = ensure_deps(
        project_env, args, platform_ref=platform_ref, force=False
    )
    return ensure_app(
        project_env,
        args,
        parent_ref=deps_ref or platform_ref,
        force=force_rebuild_requested(),
    )
