import json
import os
import subprocess
import sys

import pip._vendor.packaging.version as pip_ver
from pip._internal.operations.freeze import freeze
from pip._vendor.packaging.utils import canonicalize_name

from .. import constants
from ..bake_venv import (
    build_spec_from_config,
    detect_uv_info,
    install_fresh,
    run_pip_command,
)
from .exceptions import VenvError
from .logger import get_module_logger
from .utils import delete_files_in_directory, resolve_venv_mode

_logger = get_module_logger(__name__)


class VirtualenvChecker:
    def __init__(self, config):
        self.venv_mode = resolve_venv_mode(config)
        self.docker_venv_dir = config.get("docker_venv_dir", "")
        self.docker_project_dir = config["docker_project_dir"]
        self.requirements_txt = config.get("requirements_txt", [])
        self.odoo_requirements_path = os.path.join(
            config["docker_odoo_dir"], "requirements.txt"
        )
        self.venv_lock_file_path = os.path.join(self.docker_venv_dir, ".lock")
        self.python_version = config["python_version"]
        self.venv_lock_hash = config["venv_lock_hash"]
        self.arch = config["arch"]
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
        activate_path = self.find_file(self.docker_venv_dir, "activate")
        venv_bin_dir = os.path.dirname(activate_path)
        venv_lib_path = os.path.join(
            self.docker_venv_dir, "lib", f"python{self.python_version}", "site-packages"
        )
        os.environ["PATH"] = venv_bin_dir + os.pathsep + os.environ["PATH"]
        sys.path.insert(1, venv_lib_path)

    def package_installation_error(self, txt: str) -> None:
        _logger.error(txt)
        raise VenvError(txt)

    def _run_pip_command(self, command: str) -> None:
        run_pip_command(command, cwd=self.docker_project_dir)

    def recreate_uv_venv(self):
        delete_files_in_directory(self.docker_venv_dir)
        spec = build_spec_from_config(
            {
                "docker_project_dir": self.docker_project_dir,
                "docker_venv_dir": self.docker_venv_dir,
                "docker_odoo_dir": os.path.dirname(self.odoo_requirements_path),
                "requirements_txt": self.requirements_txt,
                "python_version": self.python_version,
            }
        )
        install_fresh(
            spec,
            use_uv=self.use_uv,
            lock_file_path=self.venv_lock_file_path,
            lock_hash=self.venv_lock_hash,
        )

    def _canonical_package_name(self, name: str) -> str:
        return canonicalize_name(name.strip())

    def sync_extra_requirements(self) -> None:
        """Install or adjust only extra packages from requirements_txt (fresh mode)."""
        separator = " "
        if self.use_uv:
            manager_commad = "uv"
            options = "--link-mode=copy"
            dir_for_venv = os.path.join(self.docker_venv_dir, "..")
            os.chdir(dir_for_venv)
            json_pip_list_bytes = subprocess.run(
                ["uv pip list --format json"],
                capture_output=True,
                shell=True,
            )
            json_pip_list_string = json_pip_list_bytes.stdout.decode("utf-8").strip()
            list_of_installed_packages = json.loads(json_pip_list_string)
        else:
            manager_commad = "python3 -m"
            options = ""
            list_of_installed_packages = [
                {"name": pkg.split("==")[0], "version": pkg.split("==")[1]}
                for pkg in freeze()
            ]
        all_instructions = {}
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
        string_to_remove = separator.join(
            [
                package_to_remove.get("full_package_name", "")
                for package_to_remove in all_instructions.get("remove", [])
            ]
        )
        if string_to_remove:
            self._run_pip_command(
                f"{manager_commad} pip remove {string_to_remove} {options}".strip()
            )
        string_to_install = separator.join(
            [
                package_to_remove.get("full_package_name", "")
                for package_to_remove in all_instructions.get("install", [])
            ]
        )
        if string_to_install:
            self._run_pip_command(
                f"{manager_commad} pip install {string_to_install} {options}".strip()
            )

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
