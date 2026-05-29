import json
import os
import shutil
import subprocess
import sys
import venv

import pip._vendor.packaging.version as pip_ver
from logger import get_module_logger
from pip._internal.operations.freeze import freeze
from pip._vendor.packaging.markers import Marker, default_environment
from pip._vendor.packaging.utils import canonicalize_name
from utils import delete_files_in_directory

_logger = get_module_logger(__name__)


class VirtualenvChecker:
    def __init__(self, config):
        self.docker_venv_dir = config.get("docker_venv_dir", "")
        self.docker_project_dir = config["docker_project_dir"]
        self.requirements_txt = config.get("requirements_txt", [])
        self.use_uv = False
        self.odoo_requirements_path = os.path.join(
            config["docker_odoo_dir"], "requirements.txt"
        )
        self.venv_lock_file_path = os.path.join(self.docker_venv_dir, ".lock")
        self.python_version = config["python_version"]
        self.venv_lock_hash = config["venv_lock_hash"]
        self.arch = config["arch"]
        self.packages_to_install = ["wheel"]
        self.uv_info = self.check_uv_installed()
        if self.uv_info.get("installed"):
            self.use_uv = True
        self.check_uv_virtual_env()

    def compare_versions(self, ver1: str, ver2: str) -> int:
        """
        Returns: -1 if ver1 < ver2, 0 if ver1 == ver2, 1 if ver1 > ver2
        """
        v1 = pip_ver.parse(ver1)
        v2 = pip_ver.parse(ver2)
        return (v1 > v2) - (v1 < v2)

    def check_uv_installed(self) -> dict:
        """
        Checks for the presence and functionality of uv in the system.
        :return: dict with keys: installed, path, version, error
        """
        uv_path = shutil.which("uv")
        if not uv_path:
            return {
                "installed": False,
                "path": None,
                "version": None,
                "error": "Executable 'uv' not found in PATH",
            }

        try:
            # Проверяем, что uv отвечает на --version (таймаут 3 сек)
            result = subprocess.run(
                [uv_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            )
            version = result.stdout.strip()
            return {
                "installed": True,
                "path": uv_path,
                "version": version,
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "installed": False,
                "path": uv_path,
                "version": None,
                "error": "uv timed out during --version execution",
            }
        except subprocess.CalledProcessError as e:
            return {
                "installed": False,
                "path": uv_path,
                "version": None,
                "error": f"uv вернул ошибку: {e.stderr.strip()}",
            }
        except Exception as e:
            return {
                "installed": False,
                "path": uv_path,
                "version": None,
                "error": str(e),
            }

    def get_packages_to_install_from_odoo_requiremets_txt(self):
        with open(self.odoo_requirements_path, "r") as file:
            for line in file.readlines():
                data = line.split(";")
                if len(data) == 1:
                    package = data[0].split("#")[0]
                    if package:
                        self.packages_to_install.append(package)
                    continue
                package_version, condition_of_installation_text = data
                condition_of_installation_text = condition_of_installation_text.split(
                    "#"
                )[0]
                condition_of_installation = self.evaluate_text_condition(
                    condition_of_installation_text
                )
                if condition_of_installation:
                    self.packages_to_install.append(package_version)

    def is_virtualenv(self):
        return sys.prefix != sys.base_prefix

    def find_file(self, start_dir: str, pattern: str):
        for root, dirs, files in os.walk(start_dir):
            for name in files:
                if name.find(pattern) >= 0:
                    return root + os.sep + name

        return ""

    def set_venv(self):
        # This is the heart of this script that puts you inside the virtual environment.
        # There is no need to undo this. When this script ends, your original path will
        # be restored.
        # Finding venv/bin dir
        venv_bin_dir = os.path.dirname(self.find_file(self.docker_venv_dir, "activate"))
        # Defining path to the venv's dirs
        venv_lib_path = os.path.join(
            self.docker_venv_dir, "lib", f"python{self.python_version}", "site-packages"
        )
        # Update PATH environment variable
        os.environ["PATH"] = venv_bin_dir + os.pathsep + os.environ["PATH"]
        # Inserting path to the venv's dirs in system path
        sys.path.insert(1, venv_lib_path)

    def evaluate_text_condition(self, condition_of_installation_text):
        marker = Marker(condition_of_installation_text)
        params = default_environment()
        res = marker.evaluate(params)
        return res

    def package_installation_error(self, txt):
        _logger.error(txt)
        exit(1)

    def create_venv(self):
        if not self.use_uv:
            env = venv.EnvBuilder(with_pip=True)
            env.create(self.docker_venv_dir)
        else:
            dir_for_venv = os.path.join(self.docker_venv_dir, "..")
            os.chdir(dir_for_venv)
            subprocess.run(["uv venv"], shell=True)

    def recreate_uv_venv(self):
        manager_commad = "python3 -m"
        options = ""
        if self.use_uv:
            manager_commad = "uv"
            options = "--link-mode=copy"
        delete_files_in_directory(self.docker_venv_dir)
        self.create_venv()
        self.set_venv()
        self.get_packages_to_install_from_odoo_requiremets_txt()
        subprocess.run(
            [
                f"""{manager_commad} pip install "cython<3.0" setuptools wheel {options}""".strip()
            ],
            shell=True,
        )
        for package in self.packages_to_install:
            if "gevent" in package:
                package = f"{package} --no-build-isolation"
                package = package.replace("<", "=").replace(">", "=")
                exit_code = os.system(
                    f"""{manager_commad} pip install {package} {options}""".strip()
                )
                if os.WEXITSTATUS(exit_code) != 0:
                    self.package_installation_error(
                        f"""Installation of package {package} failed """
                    )

        subprocess.run(
            [
                f"{manager_commad} pip install -r {self.odoo_requirements_path} {options}".strip()
            ],
            shell=True,
        )
        for package_to_install in self.requirements_txt:
            subprocess.run(
                [
                    f"{manager_commad} pip install {package_to_install} {options}".strip()
                ],
                shell=True,
            )
        with open(self.venv_lock_file_path, "w") as f:
            f.write(self.venv_lock_hash)

    def _canonical_package_name(self, name: str) -> str:
        return canonicalize_name(name.strip())

    def _run_pip_command(self, command: str) -> None:
        result = subprocess.run(
            [command],
            capture_output=True,
            shell=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            self.package_installation_error(
                f"Command failed (exit {result.returncode}): {command}\n{stderr}"
            )

    def check_uv_venv(self):
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

    # def check_package_to_remove(self, package_string, installed_package_list):
    #     pip_ver

    def check_uv_virtual_env(self):
        if not os.path.exists(self.venv_lock_file_path):
            self.recreate_uv_venv()
        elif os.path.exists(self.venv_lock_file_path):
            with open(self.venv_lock_file_path) as f:
                content = f.readlines()
            if not content:
                self.recreate_uv_venv()
            if content and self.venv_lock_hash != content[-1]:
                self.recreate_uv_venv()
        self.set_venv()
        self.check_uv_venv()
