"""Workspace extraPaths for Pylance / Python language server (Odoo addon roots)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment

class PythonAnalysisPathsBuilder:
    """Build python.analysis.extraPaths mirroring host-side Odoo addon roots."""

    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    def build(self) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        host_ctx = self.env.host_ctx
        bootstrap = self.env.bootstrap

        def add_raw(path: str | None) -> None:
            if not path:
                return
            extra = self._workspace_extra_path(path)
            if extra is None or extra in seen:
                return
            seen.add(extra)
            paths.append(extra)

        for site_packages in self._venv_site_packages_candidates():
            if os.path.isdir(site_packages):
                add_raw(site_packages)
                break

        add_raw(bootstrap.odoo_src_dir)

        developing = bootstrap.developing_project
        if developing is not None:
            add_raw(getattr(developing, "project_path", None))

        for dependency in host_ctx.docker_layout.dependencies_projects or []:
            add_raw(getattr(dependency, "project_path", None))

        for catalog in host_ctx.addon_layout.catalogs_of_modules_data or []:
            add_raw(getattr(catalog, "subproject_dir_path", None))

        return paths

    def _venv_site_packages_candidates(self) -> list[str]:
        host_ctx = self.env.host_ctx
        venv_dir = host_ctx.docker_layout.venv_dir
        python_version = str(host_ctx.project_settings.python_version or "")
        if not venv_dir or not python_version:
            return []
        relative = os.path.join("lib", f"python{python_version}", "site-packages")
        relative_lib64 = os.path.join(
            "lib64", f"python{python_version}", "site-packages"
        )
        return [
            os.path.join(venv_dir, relative_lib64),
            os.path.join(venv_dir, relative),
        ]

    def _workspace_extra_path(self, target_path: str) -> str | None:
        if not target_path or not os.path.isdir(target_path):
            return None
        project_dir = self.env.host_ctx.project_dir
        if not project_dir:
            return os.path.abspath(target_path).replace("\\", "/")

        abs_target = os.path.realpath(target_path)
        for link_path, source_path in self._symlink_pairs():
            abs_link = os.path.abspath(link_path)
            abs_source = os.path.realpath(source_path)
            if abs_source != abs_target and abs_link != abs_target:
                continue
            relative = self._relative_under_workspace(abs_link, project_dir)
            if relative is not None:
                return relative

        relative = self._relative_under_workspace(abs_target, project_dir)
        if relative is not None:
            return relative
        return abs_target.replace("\\", "/")

    @staticmethod
    def _relative_under_workspace(path: str, project_dir: str) -> str | None:
        try:
            relative = os.path.relpath(path, project_dir)
        except ValueError:
            return None
        if relative.startswith(".."):
            return None
        return relative.replace("\\", "/")

    def _symlink_pairs(self) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        host_ctx = self.env.host_ctx

        def add(link_path: str, source_path: str) -> None:
            pair = (link_path, source_path)
            if pair in seen:
                return
            seen.add(pair)
            pairs.append(pair)

        for entry in host_ctx.docker_layout.symlinks_sources or []:
            add(entry.link_path, entry.source_path)

        for scan_dir in (
            host_ctx.project_dir,
            host_ctx.docker_layout.dependencies_dir,
        ):
            if not scan_dir or not os.path.isdir(scan_dir):
                continue
            for name in os.listdir(scan_dir):
                link_path = os.path.join(scan_dir, name)
                if not os.path.islink(link_path):
                    continue
                add(link_path, os.path.realpath(link_path))

        return pairs
