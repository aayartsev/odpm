import json
import os
import subprocess
import sys

import pip._vendor.packaging.version as pip_ver
from pip._vendor.packaging.utils import canonicalize_name

from .. import constants
from ..bake_venv import (
    UV_PIP_OPTIONS,
    apply_venv_env,
    build_spec_from_config,
    detect_uv_info,
    install_fresh,
    run_pip_command,
    venv_python_path,
)
from ..container_config import ContainerConfig
from .exceptions import VenvError
from ..logging import get_module_logger
from .utils import delete_files_in_directory, resolve_venv_mode

_logger = get_module_logger(__name__)


class VirtualenvChecker:
    def __init__(self, config: ContainerConfig):
        self.config = config
        self.venv_mode = resolve_venv_mode(config)
        self.docker_venv_dir = config.docker_venv_dir
        self.docker_project_dir = config.docker_project_dir
        self.requirements_txt = config.requirements_txt
        self.odoo_requirements_path = os.path.join(
            config.docker_odoo_dir, "requirements.txt"
        )
        self.venv_lock_file_path = os.path.join(self.docker_venv_dir, ".lock")
        self.python_version = config.python_version
        self.venv_lock_hash = config.venv_lock_hash
        self.arch = config.arch
        self.uv_info = detect_uv_info()
        self.use_uv = self.uv_info["installed"]
        if self.venv_mode == constants.VENV_MODE_BAKED:
            self.ensure_baked_venv()
        else:
            self.ensure_fresh_venv()

    def ensure_baked_venv(self) -> None:
        if not os.path.isdir(self.docker_venv_dir):
            self.package_installation_error(
                f"Baked virtualenv directory is missing: {self.docker_venv_dir}"
            )
        if not os.path.exists(self.venv_lock_file_path):
            self.package_installation_error(
                f"Baked virtualenv lock file is missing: {self.venv_lock_file_path}"
            )
        with open(self.venv_lock_file_path) as lock_file:
            lock_content = lock_file.read().strip()
        if not lock_content or self.venv_lock_hash != lock_content:
            self.package_installation_error("Baked virtualenv lock hash mismatch")
        self.set_venv()

    def ensure_fresh_venv(self) -> None:
        if not self._venv_lock_matches():
            self.recreate_uv_venv()
        self.set_venv()
        self.sync_extra_requirements()

    def _venv_lock_matches(self) -> bool:
        if not os.path.exists(self.venv_lock_file_path):
            return False
        with open(self.venv_lock_file_path) as lock_file:
            content = lock_file.read().strip()
        if not content:
            return False
        return self.venv_lock_hash == content

    def compare_versions(self, ver1: str, ver2: str) -> int:
        """
        Returns: -1 if ver1 < ver2, 0 if ver1 == ver2, 1 if ver1 > ver2
        """
        v1 = pip_ver.parse(ver1)
        v2 = pip_ver.parse(ver2)
        return (v1 > v2) - (v1 < v2)

    def check_uv_installed(self) -> dict:
        return self.uv_info

    def is_virtualenv(self):
        return sys.prefix != sys.base_prefix

    def find_file(self, start_dir: str, pattern: str):
        for root, dirs, files in os.walk(start_dir):
            for name in files:
                if name.find(pattern) >= 0:
                    return root + os.sep + name

        return ""

    def set_venv(self):
        apply_venv_env(self.docker_venv_dir, python_version=self.python_version)

    @property
    def _venv_python(self) -> str:
        return venv_python_path(self.docker_venv_dir)

    def package_installation_error(self, txt: str) -> None:
        _logger.error(txt)
        raise VenvError(txt)

    def _pip_list_argv(self) -> list[str]:
        if self.use_uv:
            return [
                "uv",
                "pip",
                "list",
                "--format",
                "json",
                *UV_PIP_OPTIONS,
                "--python",
                self._venv_python,
            ]
        return [self._venv_python, "-m", "pip", "freeze"]

    def _pip_install_argv(self, *packages: str) -> list[str]:
        if self.use_uv:
            return [
                "uv",
                "pip",
                "install",
                *UV_PIP_OPTIONS,
                "--python",
                self._venv_python,
                *packages,
            ]
        return [self._venv_python, "-m", "pip", "install", *packages]

    def _pip_remove_argv(self, *packages: str) -> list[str]:
        if self.use_uv:
            return [
                "uv",
                "pip",
                "uninstall",
                *UV_PIP_OPTIONS,
                "--python",
                self._venv_python,
                *packages,
            ]
        return [self._venv_python, "-m", "pip", "uninstall", "-y", *packages]

    def _run_pip_command(self, command: str | list[str]) -> None:
        run_pip_command(
            command,
            cwd=self.docker_project_dir,
            venv_dir=self.docker_venv_dir,
        )

    def recreate_uv_venv(self):
        delete_files_in_directory(self.docker_venv_dir)
        spec = build_spec_from_config(self.config)
        install_fresh(
            spec,
            use_uv=self.use_uv,
            lock_file_path=self.venv_lock_file_path,
            lock_hash=self.venv_lock_hash,
        )

    def _canonical_package_name(self, name: str) -> str:
        return canonicalize_name(name.strip())

    def _list_installed_packages(self) -> list[dict]:
        result = subprocess.run(
            self._pip_list_argv(),
            capture_output=True,
            cwd=self.docker_project_dir,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            message = f"pip list failed (exit {result.returncode}): {stderr}"
            self.package_installation_error(message)
        if self.use_uv:
            json_pip_list_string = result.stdout.decode("utf-8").strip()
            if not json_pip_list_string:
                return []
            try:
                payload = json.loads(json_pip_list_string)
            except json.JSONDecodeError as exc:
                self.package_installation_error(
                    f"uv pip list returned invalid JSON: {exc}"
                )
            if not isinstance(payload, list):
                self.package_installation_error(
                    "uv pip list returned unexpected JSON (expected a list)"
                )
            return payload
        return [
            {"name": pkg.split("==")[0], "version": pkg.split("==")[1]}
            for pkg in result.stdout.decode("utf-8").splitlines()
            if "==" in pkg
        ]

    def sync_extra_requirements(self) -> None:
        """Install or adjust only extra packages from requirements_txt (fresh mode)."""
        list_of_installed_packages = self._list_installed_packages()
        all_instructions: dict[str, list[dict]] = {}
        for package_to_install in self.requirements_txt:
            instructions_for_package = self.check_package_to_install(
                package_to_install, list_of_installed_packages
            )
            if not instructions_for_package:
                continue
            for instruction in instructions_for_package:
                command = instruction.get("command")
                package_name = instruction.get("name")
                package_version = instruction.get("version")
                full_package_name = f"{package_name}"
                if package_version:
                    full_package_name = f"{package_name}=={package_version}"
                if command not in all_instructions:
                    all_instructions[command] = []
                all_instructions[command].append(
                    {
                        "package_version": package_version,
                        "package_name": package_name,
                        "full_package_name": full_package_name,
                    }
                )
        remove_packages = [
            package.get("full_package_name", "")
            for package in all_instructions.get("remove", [])
            if package.get("full_package_name")
        ]
        if remove_packages:
            self._run_pip_command(self._pip_remove_argv(*remove_packages))
        install_packages = [
            package.get("full_package_name", "")
            for package in all_instructions.get("install", [])
            if package.get("full_package_name")
        ]
        if install_packages:
            self._run_pip_command(self._pip_install_argv(*install_packages))

    def check_package_to_install(self, package_string, installed_package_list):
        instructions = []
        to_install_package_version = None
        if "==" in package_string:
            to_install_package_name = package_string.split("==")[0]
            to_install_package_version = package_string.split("==")[1]
        else:
            to_install_package_name = package_string

        required_name = self._canonical_package_name(to_install_package_name)

        for installed_package_info in installed_package_list:
            installed_package_name = installed_package_info.get("name")
            installed_package_version = installed_package_info.get("version")
            if required_name != self._canonical_package_name(installed_package_name):
                continue

            if to_install_package_version is None:
                return []

            compare_result = self.compare_versions(
                to_install_package_version, installed_package_version
            )
            if compare_result == 0:
                return []
            if compare_result < 0:
                return []

            instructions.append(
                {
                    "command": "remove",
                    "name": installed_package_name,
                    "version": installed_package_version,
                }
            )
            instructions.append(
                {
                    "command": "install",
                    "name": to_install_package_name,
                    "version": to_install_package_version,
                }
            )
            return instructions

        instructions.append(
            {
                "command": "install",
                "name": to_install_package_name,
                "version": to_install_package_version or "",
            }
        )
        return instructions
