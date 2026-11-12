"""Ensure layered CI images (ADR-027)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
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
from ..system_check_policy import environ_from_host_context
from ..translations import _
from .fingerprint import (
    compute_app_fingerprint,
    compute_deps_fingerprint,
    compute_lint_fingerprint,
    compute_platform_fingerprint,
    compute_venv_fingerprint,
    layer_image_ref,
)
from .prune import prune_stale_layer_cache_tags, prune_stale_requested
from .registry import (
    force_rebuild_requested,
    image_ref_exists,
    retag_image,
)

from ..host.context import HostProjectContext
from ..host.ports import BootstrapHandle

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs
    from ..project_env import CreateProjectEnvironment

_logger = get_module_logger(__name__)


def _program_dir(host_ctx: HostProjectContext) -> str:
    return str(host_ctx.program_dir)


def _remote_target(args: OdpmCliArgs, host_ctx: HostProjectContext) -> bool:
    """Whether presence checks should use the remote registry (crane).

    Registry env alone is enough to *probe* remote hits; it does **not**
    imply a push (see :func:`_want_push`).
    """
    environ = environ_from_host_context(host_ctx)
    push = resolve_ci_image_push(args, environ=environ)
    registry = os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    return bool(push or registry)


def _want_push(args: OdpmCliArgs, host_ctx: HostProjectContext) -> bool:
    """Explicit push only (``--image-push`` / ``ODPM_CI_IMAGE_PUSH``)."""
    return bool(
        resolve_ci_image_push(args, environ=environ_from_host_context(host_ctx))
    )


def _force_this_layer(force: bool | None) -> bool:
    if force is not None:
        return force
    return force_rebuild_requested()


def _maybe_prune_stale(
    args: OdpmCliArgs,
    keep_ref: str,
    *,
    remote: bool,
) -> None:
    if not prune_stale_requested(args):
        return
    prune_stale_layer_cache_tags(keep_ref, remote=remote)


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


def _elapsed_s(started: float) -> int:
    return int(time.monotonic() - started)


def _build_image(
    *,
    host_ctx: HostProjectContext,
    args: OdpmCliArgs,
    context_dir: Path,
    dockerfile: Path,
    tag: str,
    push: bool,
) -> None:
    environ = environ_from_host_context(host_ctx)
    builder_name = resolve_ci_image_builder(args, environ=environ)
    _logger.info(
        "image build: backend=%s context=%s tag=%s",
        builder_name,
        context_dir,
        tag,
    )
    started = time.monotonic()
    spec = ImageBuildSpec(
        context_dir=str(context_dir),
        dockerfile=str(dockerfile),
        tag=tag,
        platform=f"linux/{host_ctx.project_settings.arch}",
        push=push,
        project_dir=host_ctx.project_dir,
    )
    get_ci_image_build_backend(builder_name).build(spec)
    _logger.info(
        "image build finished in %s s (backend=%s tag=%s)",
        _elapsed_s(started),
        builder_name,
        tag,
    )


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


def developing_project_path(bootstrap: BootstrapHandle) -> Path | None:
    """Resolve the developing checkout path when available."""
    developing = bootstrap.developing_project
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


def _developing_git_sha(bootstrap: BootstrapHandle) -> str:
    for key in ("ODPM_DEVELOPING_GIT_SHA", "CI_COMMIT_SHA"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    root = developing_project_path(bootstrap)
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
    dest_addons: Path,
) -> int:
    """Copy dependency trees into deps context from mapped.local (no developing)."""
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    developing = developing_project_path(bootstrap)
    dest_addons.mkdir(parents=True, exist_ok=True)
    copied = 0
    mapped = list(getattr(project_env, "mapped_folders", None) or [])
    docker_extra = str(host_ctx.docker_layout.docker_extra_addons or "")
    for item in mapped:
        local = getattr(item, "local", None)
        docker = str(getattr(item, "docker", "") or "")
        if not local or not docker_extra:
            continue
        if docker == docker_extra or not docker.startswith(f"{docker_extra}/"):
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
        stamp = Path(base_image_identity_path(project_env.host_ctx.project_dir))
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
            project_env.host_ctx.project_dir,
            expected_base_image_identity(
                project_env.host_ctx, image_ref=image_ref
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
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    program_dir = _program_dir(host_ctx)
    fp = compute_platform_fingerprint(host_ctx, program_dir=program_dir)
    ref = layer_image_ref(bootstrap, layer="platform", fingerprint=fp)
    remote = _remote_target(args, host_ctx)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image platform ensure: skip (exists) %s", ref)
        _maybe_prune_stale(args, ref, remote=remote)
        return ref

    _logger.info("image platform ensure: miss — building %s", ref)
    # Parent base ensure never inherits FORCE for this layer.
    _logger.info("image platform ensure: ensuring parent base")
    base_started = time.monotonic()
    base_ref = ensure_base(project_env, force=False)
    _logger.info(
        "image platform ensure: parent base ready (%s s) %s",
        _elapsed_s(base_started),
        base_ref,
    )
    from ..project_env.ci_image import CiImageBuilder

    context_dir = Path(host_ctx.project_dir) / ".odpm" / "platform-build-context"
    _logger.info(
        "image platform ensure: preparing build context under %s",
        context_dir,
    )
    CiImageBuilder(project_env).prepare_platform_build_context(str(context_dir))
    if not (context_dir / "odoo").exists() or not (
        context_dir / "dev_project"
    ).exists():
        raise PipelineError(
            _(
                "platform context missing odoo/ or dev_project/ under {PATH}"
            ).format(PATH=context_dir),
            exit_code=1,
        )
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
    push = _want_push(args, host_ctx)
    _logger.info("image platform ensure: starting image build")
    _build_image(
        host_ctx=host_ctx,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image platform ensure: done %s", ref)
    _maybe_prune_stale(args, ref, remote=remote)
    return ref


def ensure_venv(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
    force: bool | None = None,
) -> str:
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    program_dir = _program_dir(host_ctx)
    parent = platform_ref or args.image_from
    if not parent:
        parent = ensure_platform(project_env, args, force=False)
    fp = compute_venv_fingerprint(
        bootstrap, program_dir=program_dir, platform_ref=parent
    )
    ref = layer_image_ref(bootstrap, layer="venv", fingerprint=fp)
    remote = _remote_target(args, host_ctx)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image venv ensure: skip (exists) %s", ref)
        _maybe_prune_stale(args, ref, remote=remote)
        return ref

    _logger.info("image venv ensure: miss — building %s", ref)
    from ..project_env.ci_image import CiImageBuilder

    context_dir = Path(host_ctx.project_dir) / ".odpm" / "venv-build-context"
    _logger.info(
        "image venv ensure: preparing build context under %s", context_dir
    )
    CiImageBuilder(project_env).prepare_venv_build_context(str(context_dir))
    dockerfile = context_dir / "Dockerfile.venv"
    _copy_template(program_dir, "dockerfile_venv", dockerfile)
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
    )
    dockerfile.write_text(text, encoding="utf-8")
    push = _want_push(args, host_ctx)
    _logger.info("image venv ensure: starting image build")
    _build_image(
        host_ctx=host_ctx,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image venv ensure: done %s", ref)
    _maybe_prune_stale(args, ref, remote=remote)
    return ref


def ensure_deps(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
    force: bool | None = None,
) -> str | None:
    """Ensure deps layer. ``platform_ref`` is the parent image (venv in ADR-027)."""
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    program_dir = _program_dir(host_ctx)
    parent = platform_ref or args.image_from
    if not parent:
        # Parent ensure never inherits FORCE for this layer.
        parent = ensure_venv(project_env, args, force=False)
    fp = compute_deps_fingerprint(
        host_ctx, program_dir=program_dir, platform_ref=parent
    )
    if fp is None:
        _logger.info("image deps ensure: no dependencies — layer skipped")
        return None
    ref = layer_image_ref(bootstrap, layer="deps", fingerprint=fp)
    remote = _remote_target(args, host_ctx)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image deps ensure: skip (exists) %s", ref)
        _maybe_prune_stale(args, ref, remote=remote)
        return ref

    _logger.info("image deps ensure: miss — building %s", ref)
    context_dir = Path(host_ctx.project_dir) / ".odpm" / "deps-build-context"
    _logger.info(
        "image deps ensure: preparing build context under %s", context_dir
    )
    _logger.info("image deps ensure: resetting build context %s", context_dir)
    reset_started = time.monotonic()
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    _logger.info(
        "image deps ensure: reset done (%s s)", _elapsed_s(reset_started)
    )
    _logger.info("image deps ensure: copying dependency trees")
    copy_started = time.monotonic()
    copied = _copy_deps_extra_addons(
        project_env,
        dest_addons=context_dir / "extra-addons",
    )
    _logger.info(
        "image deps ensure: dependency copy done (%s s, %s tree(s))",
        _elapsed_s(copy_started),
        copied,
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
    push = _want_push(args, host_ctx)
    _logger.info("image deps ensure: starting image build")
    _build_image(
        host_ctx=host_ctx,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image deps ensure: done %s", ref)
    _maybe_prune_stale(args, ref, remote=remote)
    return ref


def ensure_app(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    parent_ref: str | None = None,
    force: bool | None = None,
) -> str:
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    program_dir = _program_dir(host_ctx)
    developing_sha = _developing_git_sha(bootstrap)
    parent = parent_ref or args.image_from
    if not parent:
        deps_ref = ensure_deps(project_env, args, force=False)
        parent = deps_ref or ensure_venv(project_env, args, force=False)

    push = _want_push(args, host_ctx)
    publish_tag = args.image_tag or host_ctx.docker_layout.odoo_ci_image_name
    remote = _remote_target(args, host_ctx)
    secrets_baked = bool(
        os.environ.get("ODPM_BAKE_SECRETS", "").strip()
        in {"1", "true", "True", "yes", "YES"}
    )
    app_fp = compute_app_fingerprint(
        host_ctx,
        program_dir=program_dir,
        parent_ref=parent,
        developing_git_sha=developing_sha,
        secrets_baked=secrets_baked,
    )
    cache_ref = layer_image_ref(bootstrap, layer="app", fingerprint=app_fp)
    force_this = _force_this_layer(force)
    if image_ref_exists(cache_ref, remote=remote, force=force_this):
        _logger.info("image app ensure: skip (exists) %s", cache_ref)
        _publish_alias(
            cache_ref=cache_ref,
            publish_tag=publish_tag,
            push=push,
        )
        _maybe_prune_stale(args, cache_ref, remote=remote)
        return publish_tag or cache_ref

    _logger.info(
        "image app ensure: miss — building cache %s (publish %s) FROM %s",
        cache_ref,
        publish_tag,
        parent,
    )
    from ..project_env.ci_image import CiImageBuilder

    context_dir = Path(host_ctx.project_dir) / ".odpm" / "app-build-context"
    _logger.info(
        "image app ensure: preparing build context under %s", context_dir
    )
    CiImageBuilder(project_env).prepare_app_build_context(str(context_dir))
    dockerfile = context_dir / "Dockerfile.app"
    _copy_template(program_dir, "dockerfile_app", dockerfile)
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
    )
    secrets_src = context_dir / "runtime" / "secrets.json"
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
        program_dir, "dockerignore_app", context_dir / ".dockerignore"
    )
    # Push only when explicitly requested; registry env alone is for presence.
    _logger.info("image app ensure: starting image build")
    _build_image(
        host_ctx=host_ctx,
        args=args,
        context_dir=context_dir,
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
    _maybe_prune_stale(args, cache_ref, remote=remote)
    return publish_tag or cache_ref


def _lint_copy_block(*, has_hooks: bool) -> str:
    """Build COPY lines injected into dockerfile_lint before USER/RUN bake."""
    owner = "${CONTAINER_USER}:${CONTAINER_USER}"
    lines = [
        f"COPY --chown={owner} .pre-commit-config.yaml .pre-commit-config.yaml",
    ]
    if has_hooks:
        lines.append(
            f"COPY --chown={owner} .pre-commit-hooks.yaml .pre-commit-hooks.yaml"
        )
    lines.append(
        f"COPY --chown={owner} "
        "dev_project/bake_pre_commit.py "
        "dev_project/bake_pre_commit.py"
    )
    return "\n".join(lines) + "\n"


def _inject_lint_copy_block(dockerfile_text: str, *, has_hooks: bool) -> str:
    marker = "USER ${CONTAINER_USER}\n"
    if marker not in dockerfile_text:
        raise ConfigError(
            _("layered dockerfile_lint missing USER ${CONTAINER_USER} before bake")
        )
    return dockerfile_text.replace(
        marker, _lint_copy_block(has_hooks=has_hooks) + marker, 1
    )


def ensure_lint(
    project_env: CreateProjectEnvironment,
    args: OdpmCliArgs,
    *,
    platform_ref: str | None = None,
    force: bool | None = None,
) -> str:
    bootstrap = project_env.bootstrap
    host_ctx = project_env.host_ctx
    program_dir = _program_dir(host_ctx)
    pre_commit = Path(host_ctx.project_dir) / ".pre-commit-config.yaml"
    if not pre_commit.is_file():
        raise ConfigError(
            _(
                "image lint ensure requires .pre-commit-config.yaml in the "
                "project root after sources prepare"
            )
        )
    bake_src = Path(program_dir) / "dev_project" / "bake_pre_commit.py"
    if not bake_src.is_file():
        raise ConfigError(
            _(
                "missing bake_pre_commit module at {PATH} "
                "(odpm install incomplete)"
            ).format(PATH=str(bake_src))
        )
    platform_fp = compute_platform_fingerprint(host_ctx, program_dir=program_dir)
    parent = platform_ref or args.image_from
    if not parent:
        parent = ensure_platform(project_env, args, force=False)
    fp = compute_lint_fingerprint(
        host_ctx, program_dir=program_dir, platform_fp=platform_fp
    )
    ref = layer_image_ref(bootstrap, layer="lint", fingerprint=fp)
    remote = _remote_target(args, host_ctx)
    if image_ref_exists(
        ref, remote=remote, force=_force_this_layer(force)
    ):
        _logger.info("image lint ensure: skip (exists) %s", ref)
        _maybe_prune_stale(args, ref, remote=remote)
        return ref

    _logger.info("image lint ensure: miss — building %s", ref)
    context_dir = Path(host_ctx.project_dir) / ".odpm" / "lint-build-context"
    _logger.info(
        "image lint ensure: preparing build context under %s", context_dir
    )
    _logger.info("image lint ensure: resetting build context %s", context_dir)
    reset_started = time.monotonic()
    if context_dir.exists():
        shutil.rmtree(context_dir)
    context_dir.mkdir(parents=True)
    _logger.info(
        "image lint ensure: reset done (%s s)", _elapsed_s(reset_started)
    )
    _logger.info("image lint ensure: copying lint context files")
    copy_started = time.monotonic()
    shutil.copy2(pre_commit, context_dir / ".pre-commit-config.yaml")
    hooks = Path(host_ctx.project_dir) / ".pre-commit-hooks.yaml"
    has_hooks = hooks.is_file()
    if has_hooks:
        shutil.copy2(hooks, context_dir / ".pre-commit-hooks.yaml")
    bake_dest_dir = context_dir / "dev_project"
    bake_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bake_src, bake_dest_dir / "bake_pre_commit.py")
    _logger.info(
        "image lint ensure: lint context copy done (%s s)",
        _elapsed_s(copy_started),
    )
    dockerfile = context_dir / "Dockerfile.lint"
    _copy_template(program_dir, "dockerfile_lint", dockerfile)
    text = _rewrite_from_line(
        dockerfile.read_text(encoding="utf-8"),
        arg_name="PLATFORM_IMAGE",
        image_ref=parent,
    )
    text = _inject_lint_copy_block(text, has_hooks=has_hooks)
    dockerfile.write_text(text, encoding="utf-8")
    _copy_template(
        program_dir, "dockerignore_lint", context_dir / ".dockerignore"
    )
    push = _want_push(args, host_ctx)
    _logger.info("image lint ensure: starting image build")
    _build_image(
        host_ctx=host_ctx,
        args=args,
        context_dir=context_dir,
        dockerfile=dockerfile,
        tag=ref,
        push=push,
    )
    _logger.info("image lint ensure: done %s", ref)
    _maybe_prune_stale(args, ref, remote=remote)
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
    if layer == cli_params.IMAGE_VENV_LAYER:
        return ensure_venv(project_env, args, force=force)
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
    """Shortcut used by ``odpm build``: base → platform → venv → deps? → app.

    ``ODPM_IMAGE_FORCE_REBUILD`` forces only the **app** layer here so parents
    are not rebuilt «along with» the final image (ADR-027).
    """
    ensure_base(project_env, force=False)
    platform_ref = ensure_platform(project_env, args, force=False)
    venv_ref = ensure_venv(
        project_env, args, platform_ref=platform_ref, force=False
    )
    deps_ref = ensure_deps(
        project_env, args, platform_ref=venv_ref, force=False
    )
    return ensure_app(
        project_env,
        args,
        parent_ref=deps_ref or venv_ref,
        force=force_rebuild_requested(),
    )
