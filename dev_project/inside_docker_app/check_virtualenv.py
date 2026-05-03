import json
import os
import shutil
import subprocess
import sys
import venv

from logger import get_module_logger
from pip._internal.operations.freeze import freeze
from pip._vendor.packaging.markers import Marker, default_environment
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
        self.arch = config["arch"]
        self.packages_to_install = ["wheel"]
        self.uv_info = self.check_uv_installed()
        if self.uv_info.get("installed"):
            self.use_uv = True
        self.check_uv_virtual_env()

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
            f.write(self.arch)

    def check_uv_venv(self):
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
            list_of_installed_packages = [pkg for pkg in freeze()]
        for package_to_install in self.requirements_txt:
            package_is_installed = False
            for installed_package in list_of_installed_packages:
                if (
                    "==" not in package_to_install
                    and package_to_install in installed_package
                ):
                    package_is_installed = True
                if (
                    "==" in package_to_install
                    and package_to_install in installed_package
                ):
                    package_is_installed = True
            if not package_is_installed:
                json_pip_list_bytes = subprocess.run(
                    [
                        f"{manager_commad} pip install {package_to_install} {options}".strip()
                    ],
                    capture_output=True,
                    shell=True,
                )

    def check_uv_virtual_env(self):
        if not os.path.exists(self.venv_lock_file_path):
            self.recreate_uv_venv()
        elif os.path.exists(self.venv_lock_file_path):
            with open(self.venv_lock_file_path) as f:
                content = f.readlines()
            if self.arch != content[-1]:
                self.recreate_uv_venv()
        self.set_venv()
        self.check_uv_venv()
