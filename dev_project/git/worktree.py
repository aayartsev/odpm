"""Bare mirrors + per-tenant git worktrees (ADR-028).

Opt-in via ``--git-worktree`` / ``ODPM_GIT_WORKTREE``. Remote URLs only;
``file://`` stays on the classic clone path.
"""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator, Optional

from .. import constants
from ..errors import ConfigError, GitError
from ..logging import get_module_logger
from ..subprocess_runner import run_checked, run_logged
from ..translations import _

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)

ODPM_GIT_WORKTREE_ENV = "ODPM_GIT_WORKTREE"
MIRRORS_DIRNAME = "mirrors"
WORKTREES_DIRNAME = "worktrees"

_TRUTHY = frozenset({"1", "true", "True", "yes", "YES"})
_TENANT_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def git_worktree_requested(args: OdpmCliArgs | None = None) -> bool:
    """True when CLI ``--git-worktree`` or env requests bare+worktree mode."""
    # Use ``is True`` so MagicMock attributes in unit tests stay falsy.
    if args is not None and getattr(args, "git_worktree", False) is True:
        return True
    return os.environ.get(ODPM_GIT_WORKTREE_ENV, "").strip() in _TRUTHY


def tenant_id_from_project_dir(project_dir: str) -> str:
    """Basename of the odpm project directory; reject unsafe path characters."""
    tenant = os.path.basename(os.path.abspath(project_dir.rstrip(os.sep)))
    if not tenant or not _TENANT_SAFE.fullmatch(tenant):
        raise ConfigError(
            _(
                "Unsafe project directory name for git worktree tenant id: {NAME!r}. "
                "Use only letters, digits, dot, underscore, hyphen."
            ).format(NAME=tenant)
        )
    return tenant


def repo_key_from_relative_path(relative_path: str) -> str:
    """Stable filesystem key from a parsed git relative_path."""
    key = (relative_path or "").strip().lstrip("/")
    if key.endswith(".git"):
        key = key[: -len(".git")]
    key = key.strip("/")
    if not key:
        raise ConfigError(_("Cannot derive repository key from empty relative_path"))
    return key


def mirror_path(odoo_projects_dir: str, repo_key: str) -> str:
    return os.path.join(odoo_projects_dir, MIRRORS_DIRNAME, f"{repo_key}.git")


def worktree_path(odoo_projects_dir: str, tenant: str, repo_key: str) -> str:
    return os.path.join(odoo_projects_dir, WORKTREES_DIRNAME, tenant, repo_key)


def is_git_work_tree(path: str) -> bool:
    """True when ``path`` has a gitdir (directory or worktree ``.git`` file)."""
    git_meta = os.path.join(path, ".git")
    return os.path.isdir(git_meta) or os.path.isfile(git_meta)


@contextmanager
def repo_file_lock(lock_path: str) -> Iterator[None]:
    """Exclusive file lock around bare fetch / worktree create-or-recreate."""
    parent = os.path.dirname(lock_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _git_cmd(link: HandleOdooProjectLink, args: list[str]) -> list[str]:
    if link.path_to_ssh_key:
        return [
            "git",
            "-c",
            f"core.sshCommand=ssh -i {link.path_to_ssh_key}",
            *args,
        ]
    return ["git", *args]


def _run_git(
    link: HandleOdooProjectLink,
    args: list[str],
    *,
    cwd: str,
    capture: bool = True,
    check: bool = False,
):
    result = run_checked(_git_cmd(link, args), cwd=cwd, capture=capture)
    if check and result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed in {cwd!r} (exit {result.returncode})"
        )
    return result


def _rev_parse(link: HandleOdooProjectLink, cwd: str, ref: str) -> Optional[str]:
    result = _run_git(link, ["rev-parse", "--verify", ref], cwd=cwd)
    text = (result.stdout or "").strip()
    if result.returncode != 0 or not text or "fatal" in text.lower():
        return None
    return text


def head_sha(link: HandleOdooProjectLink, cwd: str) -> Optional[str]:
    return _rev_parse(link, cwd, "HEAD")


def _branch_refspec(branch: str) -> str:
    return f"+refs/heads/{branch}:refs/heads/{branch}"


def classic_clone_path(link: HandleOdooProjectLink) -> Optional[str]:
    """Path to a sibling classic working tree under ``ODOO_PROJECTS_DIR``, if any."""
    relative = ""
    project_data = getattr(link, "project_data", None)
    if project_data is not None:
        relative = getattr(project_data, "relative_path", "") or ""
    relative = (relative or "").strip().lstrip("/")
    if not relative:
        return None
    path = os.path.join(link.start_dir_to_clone, relative)
    if is_git_work_tree(path):
        return path
    return None


def _normalize_git_url(url: str) -> str:
    return (url or "").strip().rstrip(".git").rstrip("/")


def classic_remote_matches(link: HandleOdooProjectLink, classic_path: str) -> bool:
    """True when classic ``origin`` matches the link URL (same rules as check_repo_url)."""
    expected = _normalize_git_url(link.gitlink or link.project_link or "")
    if not expected:
        return False
    result = _run_git(link, ["remote", "get-url", "origin"], cwd=classic_path)
    if result.returncode != 0:
        return False
    actual = _normalize_git_url((result.stdout or "").strip())
    return actual == expected


def _set_mirror_origin_url(link: HandleOdooProjectLink, mirror: str) -> None:
    url = link.gitlink or link.project_link
    if not url:
        return
    result = _run_git(
        link, ["remote", "get-url", "origin"], cwd=mirror, capture=True
    )
    if result.returncode != 0:
        _run_git(
            link,
            ["remote", "add", "origin", url],
            cwd=mirror,
            capture=False,
            check=True,
        )
        return
    _run_git(
        link,
        ["remote", "set-url", "origin", url],
        cwd=mirror,
        capture=False,
        check=True,
    )


def _seed_bare_from_classic(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    classic_path: str,
) -> None:
    """Create bare mirror from a local classic clone; set origin to the link URL."""
    parent = os.path.dirname(mirror)
    os.makedirs(parent, exist_ok=True)
    returncode = run_logged(
        _git_cmd(link, ["clone", "--bare", classic_path, mirror]),
        cwd=parent,
    )
    if returncode != 0:
        raise GitError(
            f"git clone --bare from classic {classic_path!r} failed "
            f"(exit code {returncode})"
        )
    _set_mirror_origin_url(link, mirror)
    _logger.info(
        "Seeded bare mirror from classic clone path=%s mirror=%s",
        classic_path,
        mirror,
    )


def _fetch_ref_from_classic(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    classic_path: str,
    ref: str,
) -> bool:
    """Fetch ``ref`` from classic into bare. Returns True on success."""
    result = _run_git(
        link,
        ["fetch", classic_path, ref],
        cwd=mirror,
        capture=False,
    )
    return result.returncode == 0


def _fetch_mirror_target(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    odoo_version: Optional[str] = None,
) -> None:
    """Fetch only the target commit/branch tip into ``mirror`` (depth 1).

    Never syncs all heads/tags. On commit fetch failure raises ``GitError``
    without falling back to a wide fetch.
    """
    depth = str(constants.PLATFORM_GIT_CLONE_DEPTH)

    if link.commit_explicit and link.commit:
        result = _run_git(
            link,
            ["fetch", "--depth", depth, "origin", link.commit],
            cwd=mirror,
            capture=False,
        )
        if result.returncode != 0:
            raise GitError(
                _(
                    "Commit {COMMIT} was not fetched into bare mirror {PATH} "
                    "(exit {CODE})"
                ).format(
                    COMMIT=link.commit,
                    PATH=mirror,
                    CODE=result.returncode,
                )
            )
        return

    if link.branch_explicit and link.branch and not link.commit_explicit:
        result = _run_git(
            link,
            [
                "fetch",
                "--depth",
                depth,
                "origin",
                _branch_refspec(link.branch),
            ],
            cwd=mirror,
            capture=False,
        )
        if result.returncode != 0:
            raise GitError(
                f"git fetch failed for bare mirror {mirror!r} "
                f"branch {link.branch!r} (exit {result.returncode})"
            )
        return

    version = (odoo_version or "").strip()
    if version:
        result = _run_git(
            link,
            [
                "fetch",
                "--depth",
                depth,
                "origin",
                _branch_refspec(version),
            ],
            cwd=mirror,
            capture=False,
        )
        if result.returncode != 0:
            raise GitError(
                f"git fetch failed for bare mirror {mirror!r} "
                f"branch {version!r} (exit {result.returncode})"
            )
        return

    # Tip: default remote refspec, then HEAD — never all-heads/tags.
    result = _run_git(
        link,
        ["fetch", "--depth", depth, "origin"],
        cwd=mirror,
        capture=False,
    )
    if result.returncode == 0:
        return
    result = _run_git(
        link,
        ["fetch", "--depth", depth, "origin", "HEAD"],
        cwd=mirror,
        capture=False,
    )
    if result.returncode != 0:
        raise GitError(
            f"git fetch failed for bare mirror {mirror!r} (exit {result.returncode})"
        )


def _matching_classic(link: HandleOdooProjectLink) -> Optional[str]:
    classic = classic_clone_path(link)
    if classic and classic_remote_matches(link, classic):
        return classic
    return None


def _clone_bare_from_network(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    odoo_version: Optional[str],
) -> None:
    url = link.gitlink or link.project_link
    parent = os.path.dirname(mirror)
    clone_args = [
        "clone",
        "--bare",
        "--depth",
        str(constants.PLATFORM_GIT_CLONE_DEPTH),
    ]
    if link.branch_explicit and not link.commit_explicit:
        clone_args.extend(["-b", link.branch])
    elif (odoo_version or "").strip() and not link.commit_explicit:
        clone_args.extend(["-b", str(odoo_version).strip()])
    clone_args.extend([url, mirror])
    returncode = run_logged(_git_cmd(link, clone_args), cwd=parent)
    if returncode != 0:
        raise GitError(
            f"git clone --bare failed for {url!r} (exit code {returncode})"
        )


def _require_commit_locally(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    classic: Optional[str],
) -> None:
    """Ensure explicit commit is in bare; may fetch from classic only."""
    if not (link.commit_explicit and link.commit):
        return
    if _rev_parse(link, mirror, link.commit):
        return
    if classic and _fetch_ref_from_classic(
        link, mirror=mirror, classic_path=classic, ref=link.commit
    ):
        return
    if classic:
        raise ConfigError(
            _(
                "--no-git-update: commit {COMMIT} not found in "
                "bare mirror or classic clone"
            ).format(COMMIT=link.commit)
        )
    raise ConfigError(
        _(
            "--no-git-update: commit {COMMIT} not found in "
            "bare mirror {PATH}"
        ).format(COMMIT=link.commit, PATH=mirror)
    )


def _refresh_target_from_disk_or_origin(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    classic: Optional[str],
    skip_network: bool,
    odoo_version: Optional[str],
) -> None:
    if link.commit_explicit and link.commit and _rev_parse(link, mirror, link.commit):
        return
    if link.commit_explicit and link.commit and classic:
        _fetch_ref_from_classic(
            link, mirror=mirror, classic_path=classic, ref=link.commit
        )
        if _rev_parse(link, mirror, link.commit):
            return
        if skip_network:
            _require_commit_locally(link, mirror=mirror, classic=classic)
            return
    if skip_network:
        _require_commit_locally(link, mirror=mirror, classic=classic)
        return
    _fetch_mirror_target(link, mirror=mirror, odoo_version=odoo_version)


def ensure_bare_store(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    skip_network: bool = False,
    odoo_version: Optional[str] = None,
    fetch_target: bool = True,
) -> None:
    """Ensure bare exists (seed from classic or network); optionally narrow-fetch.

    ``skip_network`` forbids origin traffic but allows seeding / fetch from a
    matching classic clone on disk.
    """
    parent = os.path.dirname(mirror)
    os.makedirs(parent, exist_ok=True)
    classic = _matching_classic(link)

    if not os.path.isdir(mirror):
        if classic:
            _seed_bare_from_classic(link, mirror=mirror, classic_path=classic)
        elif skip_network:
            raise ConfigError(
                _(
                    "--no-git-update requires an existing bare mirror at {PATH} "
                    "or a matching classic clone to seed from"
                ).format(PATH=mirror)
            )
        else:
            _clone_bare_from_network(
                link, mirror=mirror, odoo_version=odoo_version
            )
        if fetch_target:
            _refresh_target_from_disk_or_origin(
                link,
                mirror=mirror,
                classic=classic,
                skip_network=skip_network,
                odoo_version=odoo_version,
            )
        return

    if skip_network:
        # Empty placeholder dirs (tests / partial setup): same as prior early return.
        if not os.path.isdir(os.path.join(mirror, "objects")):
            return
        if fetch_target:
            _require_commit_locally(link, mirror=mirror, classic=classic)
        return

    if fetch_target:
        _refresh_target_from_disk_or_origin(
            link,
            mirror=mirror,
            classic=classic,
            skip_network=False,
            odoo_version=odoo_version,
        )


def ensure_bare_mirror(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    skip_fetch: bool = False,
    odoo_version: Optional[str] = None,
) -> None:
    """Clone/seed bare if missing; narrow-fetch unless ``skip_fetch``."""
    ensure_bare_store(
        link,
        mirror=mirror,
        skip_network=skip_fetch,
        odoo_version=odoo_version,
        fetch_target=True,
    )


def show_blob_at_ref(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    ref: str,
    path: str,
) -> bytes:
    """Return raw file bytes from ``ref:path`` in a bare (or any) git dir."""
    cmd = _git_cmd(link, ["show", f"{ref}:{path}"])
    completed = subprocess.run(
        cmd,
        cwd=mirror,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        err = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise GitError(
            f"git show {ref}:{path} failed in {mirror!r}: {err or completed.returncode}"
        )
    return completed.stdout


def ensure_platform_bare_pin(
    link: HandleOdooProjectLink,
    *,
    odoo_version: str,
    skip_network: bool = False,
) -> str:
    """Ensure platform bare + fetch pin; return mirror path. No worktree."""
    repo_key = repo_key_from_relative_path(link.project_data.relative_path)
    root = link.start_dir_to_clone
    mirror = mirror_path(root, repo_key)
    lock = mirror + ".lock"
    with repo_file_lock(lock):
        ensure_bare_store(
            link,
            mirror=mirror,
            skip_network=skip_network,
            odoo_version=odoo_version,
            fetch_target=True,
        )
        link.worktree_mirror = mirror
    return mirror


def resolve_target_sha(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    odoo_version: Optional[str] = None,
) -> str:
    """Resolve the commit the worktree should point at (detached HEAD)."""
    if link.commit_explicit and link.commit:
        sha = _rev_parse(link, mirror, link.commit)
        if sha:
            return sha
        # May need a fetch of the specific commit (already fetched if not skip).
        raise GitError(
            f"Commit {link.commit!r} not found in bare mirror {mirror}"
        )

    candidates: list[str] = []
    if link.branch_explicit and link.branch:
        candidates.extend([link.branch, f"refs/heads/{link.branch}"])
    if odoo_version:
        candidates.extend([str(odoo_version), f"refs/heads/{odoo_version}"])
    candidates.extend(["HEAD", "refs/heads/master", "refs/heads/main"])

    for ref in candidates:
        sha = _rev_parse(link, mirror, ref)
        if sha:
            return sha
    raise GitError(f"Could not resolve a target commit in bare mirror {mirror}")


def _prune_worktrees(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
) -> None:
    """Drop bare admin entries whose checkout directories no longer exist."""
    _run_git(
        link,
        ["worktree", "prune"],
        cwd=mirror,
        capture=False,
    )


def _remove_worktree(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    wt_path: str,
) -> None:
    if os.path.isdir(wt_path) or os.path.isfile(os.path.join(wt_path, ".git")):
        result = _run_git(
            link,
            ["worktree", "remove", "--force", wt_path],
            cwd=mirror,
            capture=False,
        )
        if result.returncode != 0 and os.path.exists(wt_path):
            shutil.rmtree(wt_path, ignore_errors=True)
            _prune_worktrees(link, mirror=mirror)
    else:
        # Path gone (shared PVC / partial cleanup) but may still be registered.
        _prune_worktrees(link, mirror=mirror)


def ensure_worktree_at_sha(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    wt_path: str,
    sha: str,
    allow_update: bool,
) -> None:
    """Create or reuse worktree at ``sha``; mismatch without update → ConfigError."""
    current = None
    if is_git_work_tree(wt_path):
        current = head_sha(link, wt_path)
        if current and current == sha:
            return
        if not allow_update:
            raise ConfigError(
                _(
                    "--no-git-update: worktree at {PATH} is on {HAVE}, "
                    "expected {WANT}; refuse to recreate"
                ).format(
                    PATH=wt_path,
                    HAVE=(current or "<missing>")[:12],
                    WANT=sha[:12],
                )
            )
        _remove_worktree(link, mirror=mirror, wt_path=wt_path)
    elif os.path.exists(wt_path):
        if not allow_update:
            raise ConfigError(
                _(
                    "--no-git-update: worktree path exists but is not a git "
                    "worktree: {PATH}"
                ).format(PATH=wt_path)
            )
        shutil.rmtree(wt_path)
        _prune_worktrees(link, mirror=mirror)
    elif not allow_update:
        raise ConfigError(
            _(
                "--no-git-update requires an existing worktree at {PATH}"
            ).format(PATH=wt_path)
        )
    else:
        # Checkout missing: clear stale "already registered" entries first.
        _prune_worktrees(link, mirror=mirror)

    os.makedirs(os.path.dirname(wt_path), exist_ok=True)
    result = _run_git(
        link,
        ["worktree", "add", "--detach", wt_path, sha],
        cwd=mirror,
        capture=False,
    )
    if result.returncode != 0:
        # Belt-and-suspenders for "missing but already registered".
        _prune_worktrees(link, mirror=mirror)
        result = _run_git(
            link,
            ["worktree", "add", "--force", "--detach", wt_path, sha],
            cwd=mirror,
            capture=False,
        )
    if result.returncode != 0:
        raise GitError(
            f"git worktree add failed for {wt_path!r} at {sha[:12]} "
            f"(exit {result.returncode})"
        )


def configure_link_worktree_context(
    link: HandleOdooProjectLink,
    *,
    tenant: str,
    skip_git_update: bool,
) -> None:
    """Mark a remote link for worktree materialize (no-op for ``file://``)."""
    if link.link_type == constants.GITLINK_TYPE_FILE:
        link.worktree_mode = False
        return
    if link.link_type not in (
        constants.GITLINK_TYPE_HTTP,
        constants.GITLINK_TYPE_GIT,
        constants.GITLINK_TYPE_SSH,
    ):
        link.worktree_mode = False
        return
    link.worktree_mode = True
    link.worktree_tenant = tenant
    link.worktree_skip_update = bool(skip_git_update)
    bind_link_to_worktree_layout(link)


def bind_link_to_worktree_layout(link: HandleOdooProjectLink) -> str | None:
    """Point ``link.project_path`` at the expected tenant worktree path.

    Does not create the worktree. Used so bootstrap / ``--no-git-update``
    presence checks look under ``worktrees/<tenant>/…`` instead of the classic
    clone layout.
    """
    if getattr(link, "worktree_mode", False) is not True:
        return None
    tenant = getattr(link, "worktree_tenant", None)
    if not tenant:
        return None
    relative = ""
    project_data = getattr(link, "project_data", None)
    if project_data is not None:
        relative = getattr(project_data, "relative_path", "") or ""
    repo_key = repo_key_from_relative_path(relative)
    root = link.start_dir_to_clone
    mirror = mirror_path(root, repo_key)
    wt = worktree_path(root, tenant, repo_key)
    link.worktree_mirror = mirror
    link.project_path = wt
    link.dir_to_clone = os.path.dirname(wt)
    return wt


def _materialize_link_as_worktree_locked(
    link: HandleOdooProjectLink,
    *,
    mirror: str,
    wt_path: str,
    odoo_version: Optional[str] = None,
    fetch_target: bool = True,
) -> str:
    """Bare + worktree under an already-held repo lock."""
    allow_update = not bool(getattr(link, "worktree_skip_update", False))
    ensure_bare_store(
        link,
        mirror=mirror,
        skip_network=not allow_update,
        odoo_version=odoo_version,
        fetch_target=fetch_target,
    )
    link.worktree_mirror = mirror
    sha = resolve_target_sha(link, mirror=mirror, odoo_version=odoo_version)
    ensure_worktree_at_sha(
        link,
        mirror=mirror,
        wt_path=wt_path,
        sha=sha,
        allow_update=allow_update,
    )
    link.project_path = wt_path
    link.dir_to_clone = os.path.dirname(wt_path)
    link.is_cloned = True
    repo_key = repo_key_from_relative_path(link.project_data.relative_path)
    _logger.info(
        "Worktree ready tenant=%s repo=%s sha=%s path=%s",
        getattr(link, "worktree_tenant", ""),
        repo_key,
        sha[:12],
        wt_path,
    )
    return wt_path


def materialize_link_as_worktree(
    link: HandleOdooProjectLink,
    *,
    odoo_version: Optional[str] = None,
) -> str:
    """Ensure bare + worktree; set ``link.project_path`` to the worktree path."""
    tenant = getattr(link, "worktree_tenant", None)
    if not tenant:
        raise ConfigError(_("worktree_tenant is not set on git link"))
    repo_key = repo_key_from_relative_path(link.project_data.relative_path)
    root = link.start_dir_to_clone
    mirror = mirror_path(root, repo_key)
    wt = worktree_path(root, tenant, repo_key)
    lock = mirror + ".lock"

    with repo_file_lock(lock):
        return _materialize_link_as_worktree_locked(
            link,
            mirror=mirror,
            wt_path=wt,
            odoo_version=odoo_version,
            fetch_target=True,
        )


def materialize_platform_worktree(
    link: HandleOdooProjectLink,
    *,
    odoo_version: str,
    apply_build_date_fn=None,
) -> str:
    """Platform: bare (+seed) → optional ``apply_build_date_fn`` → one worktree.

    ``apply_build_date_fn`` is a zero-arg callable (already bound to date/version).
    One mirror lock — no tip worktree before the date resolves.
    """
    tenant = getattr(link, "worktree_tenant", None)
    if not tenant:
        raise ConfigError(_("worktree_tenant is not set on git link"))
    repo_key = repo_key_from_relative_path(link.project_data.relative_path)
    root = link.start_dir_to_clone
    mirror = mirror_path(root, repo_key)
    wt = worktree_path(root, tenant, repo_key)
    lock = mirror + ".lock"
    allow_update = not bool(getattr(link, "worktree_skip_update", False))

    with repo_file_lock(lock):
        ensure_bare_store(
            link,
            mirror=mirror,
            skip_network=not allow_update,
            odoo_version=odoo_version,
            fetch_target=True,
        )
        link.worktree_mirror = mirror
        link.project_path = wt
        link.dir_to_clone = os.path.dirname(wt)
        if apply_build_date_fn is not None:
            try:
                apply_build_date_fn()
            except (GitError, RuntimeError, ValueError) as error:
                if not allow_update:
                    raise ConfigError(
                        _(
                            "--no-git-update: cannot resolve odoo_build_date from "
                            "local bare/classic history: {ERROR}"
                        ).format(ERROR=error)
                    ) from error
                raise
        sha = resolve_target_sha(link, mirror=mirror, odoo_version=odoo_version)
        ensure_worktree_at_sha(
            link,
            mirror=mirror,
            wt_path=wt,
            sha=sha,
            allow_update=allow_update,
        )
        link.project_path = wt
        link.dir_to_clone = os.path.dirname(wt)
        link.is_cloned = True
        link.worktree_mirror = mirror
        _logger.info(
            "Worktree ready tenant=%s repo=%s sha=%s path=%s",
            tenant,
            repo_key,
            sha[:12],
            wt,
        )
        return wt


def sync_worktree_to_resolved_ref(
    link: HandleOdooProjectLink,
    *,
    odoo_version: str,
) -> None:
    """After branch/commit resolution, recreate worktree if SHA changed."""
    if getattr(link, "worktree_mode", False) is not True:
        return
    materialize_link_as_worktree(link, odoo_version=odoo_version)
