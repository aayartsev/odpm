import sys
import os
import venv
import platform
import re
import shutil

_DIGITS = re.compile(r'\d+\.\d+')

from pip._internal.operations.freeze import freeze
from pip._vendor.packaging.markers import default_environment, Marker

from utils import delete_files_in_directory
from logger import get_module_logger

_logger = get_module_logger(__name__)

class VirtualenvChecker():

    def __init__(self, config):
        self.docker_venv_dir = config.get("docker_venv_dir", "")
        self.docker_project_dir = config["docker_project_dir"]
        self.requirements_txt = config.get("requirements_txt", [])
        self.odoo_requirements_path = os.path.join(config["docker_odoo_dir"], "requirements.txt")
        self.venv_lock_file_path = os.path.join(self.docker_venv_dir, "venv.lock")
        self.python_version = config["python_version"]
        self.arch = config["arch"]
        self.check_virtual_env()

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
        # finding venv/bin dir
        venv_bin_dir = os.path.dirname(self.find_file(self.docker_venv_dir, "activate"))
        # defining path to the venv`s dirs
        venv_lib_path = os.path.join(self.docker_venv_dir,"lib",f"python{self.python_version}","site-packages")
        # update PATH environment variable
        os.environ["PATH"] = venv_bin_dir + os.pathsep + os.environ["PATH"]
        # inserting path to the venv`s dirs in system path
        sys.path.insert(1, venv_lib_path)


    def check_packages_for_install(self) -> None:
        list_of_installed_packages = [pkg for pkg in freeze()]
        for package_to_install in self.requirements_txt:
            package_is_installed = False
            for installed_package in list_of_installed_packages:
                if "==" not in package_to_install and package_to_install in installed_package:
                    package_is_installed = True
                if "==" in package_to_install and package_to_install in installed_package:
                    package_is_installed = True
            if not package_is_installed:
                os.system(f"""python3 -m pip install {package_to_install}""")

    def evaluate_text_condition(self, condition_of_installation_text):
        marker = Marker(condition_of_installation_text)
        params = default_environment()
        res = marker.evaluate(params)
        return res

    def recreate_venv(self):
        delete_files_in_directory(self.docker_venv_dir)
        self.create_venv()
        self.set_venv()
        exit_code = os.system(f"""python3 -m pip install --upgrade pip""")
        if os.WEXITSTATUS(exit_code) != 0:
            self.package_installation_error(f"""Upgrade of pip was failed """)
        packages_to_install = ["wheel"]
        with open(self.odoo_requirements_path, "r") as file:
            for line in file.readlines():
                data = line.split(";")
                if len(data) == 1:
                    package = data[0].split("#")[0]
                    if package:
                        packages_to_install.append(package)
                    continue
                package_version, condition_of_installation_text = data
                condition_of_installation_text = condition_of_installation_text.split("#")[0]
                condition_of_installation = self.evaluate_text_condition(condition_of_installation_text)
                if condition_of_installation:
                    packages_to_install.append(package_version)
        for package in packages_to_install:
            if "gevent" in package:
                package = f"{package} --no-build-isolation"
            package = package.replace("<", "=").replace( ">", "=")
            exit_code = os.system(f"""python3 -m pip install {package}""")
            if os.WEXITSTATUS(exit_code) != 0:
                self.package_installation_error(f"""Installation of package {package} was failed """)

        for package in self.requirements_txt:
            exit_code = os.system(f"""python3 -m pip install {package}""")
            if os.WEXITSTATUS(exit_code) != 0:
                self.package_installation_error(f"""Installation of package {package} was failed """)
        with open(self.venv_lock_file_path, 'w') as f:
            f.write(self.arch)

    
    def package_installation_error(self, txt):
        _logger.error(txt)
        exit(1)
        
    
    def create_venv(self):
        env = venv.EnvBuilder(with_pip = True)
        env.create(self.docker_venv_dir)
    
    def check_virtual_env(self):
        if not os.path.exists(self.venv_lock_file_path):
            self.recreate_venv()
        elif os.path.exists(self.venv_lock_file_path):
            with open(self.venv_lock_file_path) as f:
                content = f.readlines()
            if self.arch != content[0]:
                self.recreate_venv()
        self.set_venv()
        self.check_packages_for_install()