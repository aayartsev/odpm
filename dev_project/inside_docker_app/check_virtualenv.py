import os

from .. import constants
from ..bake_venv import (
    UV_PIP_INSTALL_OPTIONS,
    apply_venv_env,
    build_spec_from_config,
    detect_uv_info,
    install_fresh,
    run_pip_command,
    venv_python_path,
)
from ..config.payload import compute_extras_stamp
from ..container_config import ContainerConfig
from .exceptions import VenvError
from ..logging import get_module_logger
from .extras_sync import (
    managed_distribution_names,
    read_extras_lock,
    write_extras_lock,
    write_extras_requirements_file,
)
from .utils import delete_files_in_directory, resolve_venv_mode
from .venv_import_smoke import verify_venv_import_smoke

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
        self.extras_lock_file_path = os.path.join(
            self.docker_venv_dir, constants.VENV_EXTRAS_LOCK_BASENAME
        )
        self.extras_requirements_path = os.path.join(
            self.docker_venv_dir, constants.VENV_EXTRAS_REQUIREMENTS_BASENAME
        )
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
        verify_venv_import_smoke()

    def ensure_fresh_venv(self) -> None:
        if not self._venv_lock_matches():
            self.recreate_uv_venv()
        else:
            self.sync_extras_requirements()
        self.set_venv()
        if verify_venv_import_smoke(raise_on_failure=False):
            return
        _logger.warning(
            "Virtualenv import smoke failed with matching lock; recreating venv"
        )
        self.recreate_uv_venv()
        self.set_venv()
        verify_venv_import_smoke()

    def _venv_lock_matches(self) -> bool:
        if not os.path.exists(self.venv_lock_file_path):
            return False
        with open(self.venv_lock_file_path) as lock_file:
            content = lock_file.read().strip()
        if not content:
            return False
        return self.venv_lock_hash == content

    def _extras_stamp(self) -> str:
        return compute_extras_stamp(self.requirements_txt)

    def _extras_lock_matches(self) -> bool:
        state = read_extras_lock(self.extras_lock_file_path)
        if state is None:
            return False
        return state.stamp == self._extras_stamp()

    def check_uv_installed(self) -> dict:
        return self.uv_info

    def is_virtualenv(self):
        import sys

        return sys.prefix != sys.base_prefix

    def set_venv(self):
        apply_venv_env(self.docker_venv_dir, python_version=self.python_version)

    @property
    def _venv_python(self) -> str:
        return venv_python_path(self.docker_venv_dir)

    def package_installation_error(self, txt: str) -> None:
        _logger.error(txt)
        raise VenvError(txt)

    def _pip_install_requirements_argv(self, requirements_path: str) -> list[str]:
        if self.use_uv:
            return [
                "uv",
                "pip",
                "install",
                *UV_PIP_INSTALL_OPTIONS,
                "--python",
                self._venv_python,
                "-r",
                requirements_path,
            ]
        return [self._venv_python, "-m", "pip", "install", "-r", requirements_path]

    def _pip_remove_argv(self, *packages: str) -> list[str]:
        if self.use_uv:
            return [
                "uv",
                "pip",
                "uninstall",
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

    def _write_extras_lock_file(self) -> None:
        write_extras_lock(
            self.extras_lock_file_path,
            stamp=self._extras_stamp(),
            distributions=managed_distribution_names(self.requirements_txt),
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
        self._write_extras_lock_file()

    def sync_extras_requirements(self) -> None:
        """Install extras via pip -r; uninstall managed packages removed from config."""
        if self._extras_lock_matches():
            return

        current_distributions = managed_distribution_names(self.requirements_txt)
        previous = read_extras_lock(self.extras_lock_file_path)
        previous_distributions = previous.distributions if previous else []

        to_remove = sorted(set(previous_distributions) - set(current_distributions))
        if to_remove:
            self._run_pip_command(self._pip_remove_argv(*to_remove))

        requirement_lines = [
            req.strip() for req in self.requirements_txt if req and req.strip()
        ]
        if requirement_lines:
            write_extras_requirements_file(
                self.extras_requirements_path,
                self.requirements_txt,
            )
            self._run_pip_command(
                self._pip_install_requirements_argv(self.extras_requirements_path)
            )

        self._write_extras_lock_file()
