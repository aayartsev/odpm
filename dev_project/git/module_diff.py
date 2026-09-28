"""Classify Odoo modules changed since a git baseline (developing repo)."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .. import constants
from ..errors import ConfigError
from ..subprocess_runner import run_checked
from ..translations import _


@dataclass(frozen=True)
class ModuleDiffResult:
    init_modules: str
    update_modules: str
    base: str
    head: str


@dataclass(frozen=True)
class LastAppliedMarker:
    developing_sha: str
    applied_at: str


def last_applied_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_DEPLOY_LAST_APPLIED_REL_PATH)


def ensure_deploy_gitignore(project_dir: str) -> None:
    odpm_dir = os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY)
    os.makedirs(odpm_dir, exist_ok=True)
    gitignore_path = os.path.join(odpm_dir, ".gitignore")
    entry = constants.DEPLOY_GITIGNORE_ENTRY
    if not os.path.isfile(gitignore_path):
        Path(gitignore_path).write_text(f"{entry}\n", encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if entry not in existing.splitlines():
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        Path(gitignore_path).write_text(f"{existing}{suffix}{entry}\n", encoding="utf-8")


def read_last_applied(project_dir: str) -> LastAppliedMarker | None:
    path = last_applied_path(project_dir)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(_("Deploy marker must be a JSON object: {PATH}").format(PATH=path))
    sha = str(raw.get("developing_sha") or "").strip()
    applied_at = str(raw.get("applied_at") or "").strip()
    if not sha:
        raise ConfigError(
            _("Deploy marker is missing developing_sha: {PATH}").format(PATH=path)
        )
    return LastAppliedMarker(developing_sha=sha, applied_at=applied_at or "")


def write_last_applied(project_dir: str, developing_sha: str) -> str:
    ensure_deploy_gitignore(project_dir)
    deploy_dir = os.path.join(project_dir, constants.ODPM_DEPLOY_DIR_REL_PATH)
    os.makedirs(deploy_dir, exist_ok=True)
    path = last_applied_path(project_dir)
    payload = {
        "developing_sha": developing_sha,
        "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def resolve_diff_base(
    *,
    project_dir: str,
    cli_diff_base: str | None,
    environ: dict[str, str] | None = None,
) -> str:
    env = environ if environ is not None else os.environ
    if cli_diff_base is not None and str(cli_diff_base).strip():
        value = str(cli_diff_base).strip()
        if value == constants.LAST_APPLIED_SENTINEL:
            marker = read_last_applied(project_dir)
            if marker is None:
                raise ConfigError(
                    _(
                        "Deploy marker not found at {PATH}; pass --diff-base <sha|tag> "
                        "for the first apply."
                    ).format(PATH=last_applied_path(project_dir))
                )
            return marker.developing_sha
        return value

    odpm_env = str(env.get(constants.ODPM_DIFF_BASE_ENV) or "").strip()
    if odpm_env:
        if odpm_env == constants.LAST_APPLIED_SENTINEL:
            marker = read_last_applied(project_dir)
            if marker is None:
                raise ConfigError(
                    _(
                        "ODPM_DIFF_BASE=@last-applied but deploy marker is missing "
                        "at {PATH}."
                    ).format(PATH=last_applied_path(project_dir))
                )
            return marker.developing_sha
        return odpm_env

    ci_sha = str(env.get(constants.CI_MERGE_REQUEST_DIFF_BASE_SHA_ENV) or "").strip()
    if ci_sha:
        return ci_sha

    marker = read_last_applied(project_dir)
    if marker is not None:
        return marker.developing_sha

    raise ConfigError(
        _(
            "No git diff baseline: set --diff-base, {ENV}, "
            "{CI_ENV}, or create {PATH} via odpm modules record-applied."
        ).format(
            ENV=constants.ODPM_DIFF_BASE_ENV,
            CI_ENV=constants.CI_MERGE_REQUEST_DIFF_BASE_SHA_ENV,
            PATH=last_applied_path(project_dir),
        )
    )


def developing_repo_path(config) -> str:
    developing = getattr(config, "developing_project", None)
    path = str(getattr(developing, "project_path", "") or "").strip()
    if not path or not os.path.isdir(path):
        raise ConfigError(
            _(
                "Developing project path is missing or not a directory; "
                "run a normal odpm prepare first."
            )
        )
    if not os.path.isdir(os.path.join(path, ".git")) and not os.path.isfile(
        os.path.join(path, ".git")
    ):
        raise ConfigError(
            _("Developing project is not a git repository: {PATH}").format(PATH=path)
        )
    return path


def git_rev_parse(repo_path: str, ref: str) -> str:
    result = run_checked(["git", "rev-parse", "--verify", ref], cwd=repo_path)
    if result.returncode != 0:
        raise ConfigError(
            _(
                "Git ref {REF!r} is not available in {PATH} "
                "(fetch the base commit if this is a shallow clone)."
            ).format(REF=ref, PATH=repo_path)
        )
    return result.stdout.strip()


def _module_rel_dir_for_path(repo_root: Path, rel_path: str) -> Path | None:
    rel = Path(rel_path)
    cur = rel.parent if rel.parts else Path(".")
    while True:
        abs_dir = repo_root / cur
        for name in constants.MODULE_FILES:
            if (abs_dir / name).is_file():
                return cur
        if cur == Path(".") or not cur.parts:
            break
        cur = cur.parent
    return None


def _module_existed_at_base(repo_path: str, base: str, module_rel: Path) -> bool:
    for name in constants.MODULE_FILES:
        blob = f"{base}:{module_rel.as_posix()}/{name}"
        result = run_checked(["git", "cat-file", "-e", blob], cwd=repo_path)
        if result.returncode == 0:
            return True
    return False


def _parse_name_status_line(line: str) -> list[str]:
    parts = line.split("\t")
    if not parts or not parts[0]:
        return []
    status = parts[0]
    if status.startswith("R") or status.startswith("C"):
        if len(parts) >= 3:
            return [parts[2]]
        return []
    if status.startswith("D"):
        return []
    if len(parts) >= 2:
        return [parts[1]]
    return []


def classify_modules_from_diff(
    repo_path: str,
    *,
    base: str,
    head: str = "HEAD",
) -> ModuleDiffResult:
    base_sha = git_rev_parse(repo_path, base)
    head_sha = git_rev_parse(repo_path, head)
    result = run_checked(
        ["git", "diff", "--name-status", f"{base_sha}...{head_sha}"],
        cwd=repo_path,
    )
    if result.returncode != 0:
        raise ConfigError(
            _("git diff failed in {PATH}: {ERROR}").format(
                PATH=repo_path,
                ERROR=(result.stderr or result.stdout or "").strip() or "unknown error",
            )
        )

    repo_root = Path(repo_path)
    touched_dirs: set[Path] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        for rel in _parse_name_status_line(line):
            module_rel = _module_rel_dir_for_path(repo_root, rel)
            if module_rel is not None and module_rel != Path("."):
                touched_dirs.add(module_rel)

    init_names: list[str] = []
    update_names: list[str] = []
    for module_rel in sorted(touched_dirs, key=lambda p: p.as_posix()):
        tech = module_rel.name
        if _module_existed_at_base(repo_path, base_sha, module_rel):
            update_names.append(tech)
        else:
            init_names.append(tech)

    return ModuleDiffResult(
        init_modules=",".join(init_names),
        update_modules=",".join(update_names),
        base=base_sha,
        head=head_sha,
    )


def format_module_diff(result: ModuleDiffResult, fmt: str) -> str:
    if fmt == "json":
        payload = {
            "init_modules": result.init_modules,
            "update_modules": result.update_modules,
            "base": result.base,
            "head": result.head,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if fmt == "shell":
        return (
            f"export ODPM_INIT_MODULES={shlex.quote(result.init_modules)}\n"
            f"export ODPM_UPDATE_MODULES={shlex.quote(result.update_modules)}\n"
        )
    # text
    init_display = result.init_modules or "(none)"
    update_display = result.update_modules or "(none)"
    return (
        f"base: {result.base}\n"
        f"head: {result.head}\n"
        f"init: {init_display}\n"
        f"update: {update_display}\n"
    )


def compute_module_diff_for_config(
    config,
    *,
    cli_diff_base: str | None,
    environ: dict[str, str] | None = None,
) -> ModuleDiffResult:
    project_dir = str(getattr(config, "project_dir", "") or "")
    if not project_dir:
        raise ConfigError(_("Project directory is not set."))
    repo_path = developing_repo_path(config)
    base = resolve_diff_base(
        project_dir=project_dir,
        cli_diff_base=cli_diff_base,
        environ=environ,
    )
    return classify_modules_from_diff(repo_path, base=base)
