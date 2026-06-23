"""Shared virtualenv installation for dev container and CI image bake."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import venv
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from packaging.markers import Marker, default_environment
except ImportError:
    from pip._vendor.packaging.markers import Marker, default_environment

from . import constants
from .container_config import ContainerConfig
from .inside_docker_app.exceptions import VenvError
from .logging import get_module_logger


_logger = get_module_logger(__name__)

UV_PIP_INSTALL_OPTIONS = ("--link-mode=copy",)


def venv_python_path(venv_dir: str) -> str:
    return os.path.join(venv_dir, "bin", "python3")


def apply_venv_env(venv_dir: str, *, python_version: str | None = None) -> str:
    """Expose venv on PATH/VIRTUAL_ENV for pip/uv; return venv python path."""
    python_path = venv_python_path(venv_dir)
    bin_dir = os.path.dirname(python_path)
    os.environ["VIRTUAL_ENV"] = venv_dir
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    if python_version is not None:
        lib_path = os.path.join(
            venv_dir, "lib", f"python{python_version}", "site-packages"
        )
        if lib_path not in sys.path:
            sys.path.insert(1, lib_path)
    return python_path


@dataclass
class VenvInstallSpec:
    project_dir: str
    venv_dir: str
    odoo_requirements_path: str
    extra_packages: list[str]
    python_version: str
    bootstrap_packages: list[str] = field(default_factory=list)
    lock_file_path: str | None = None
    lock_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VenvInstallSpec:
        return cls(
            project_dir=data["project_dir"],
            venv_dir=data["venv_dir"],
            odoo_requirements_path=data["odoo_requirements_path"],
            extra_packages=list(data.get("extra_packages") or []),
            python_version=data["python_version"],
            bootstrap_packages=list(data.get("bootstrap_packages") or []),
            lock_file_path=data.get("lock_file_path"),
            lock_hash=data.get("lock_hash"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> VenvInstallSpec:
        with open(path) as config_file:
            return cls.from_dict(json.load(config_file))


@dataclass(frozen=True)
class PipRunner:
    base_cmd: list[str]
    pip_extra_args: list[str]
    cwd: str

    def install(self, *packages: str) -> None:
        if not packages:
            return
        cmd = [*self.base_cmd, "pip", "install", *self.pip_extra_args, *packages]
        _run_subprocess(cmd, cwd=self.cwd)

    def install_requirements(self, requirements_path: str) -> None:
        cmd = [
            *self.base_cmd,
            "pip",
            "install",
            *self.pip_extra_args,
            "-r",
            requirements_path,
        ]
        _run_subprocess(cmd, cwd=self.cwd)

    def install_gevent(self, package: str) -> None:
        gevent_spec = package.replace("<", "=").replace(">", "=")
        cmd = [
            *self.base_cmd,
            "pip",
            "install",
            *self.pip_extra_args,
            gevent_spec,
            "--no-build-isolation",
        ]
        _run_subprocess(cmd, cwd=self.cwd)


def get_venv_bootstrap_packages(python_version: str) -> list[str]:
    return constants.VENV_BOOTSTRAP_PACKAGES.get(
        python_version,
        constants.DEFAULT_VENV_BOOTSTRAP + ["setuptools"],
    )


def resolve_bootstrap_packages(spec: VenvInstallSpec) -> list[str]:
    if spec.bootstrap_packages:
        return spec.bootstrap_packages
    return get_venv_bootstrap_packages(spec.python_version)


def detect_uv_info() -> dict[str, Any]:
    uv_path = shutil.which("uv")
    if not uv_path:
        return {
            "installed": False,
            "path": None,
            "version": None,
            "error": "Executable 'uv' not found in PATH",
        }
    try:
        result = subprocess.run(
            [uv_path, "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return {
            "installed": True,
            "path": uv_path,
            "version": result.stdout.strip(),
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "installed": False,
            "path": uv_path,
            "version": None,
            "error": "uv timed out during --version execution",
        }
    except subprocess.CalledProcessError as exc:
        return {
            "installed": False,
            "path": uv_path,
            "version": None,
            "error": f"uv returned error: {exc.stderr.strip()}",
        }
    except Exception as exc:
        return {
            "installed": False,
            "path": uv_path,
            "version": None,
            "error": str(exc),
        }


def detect_uv() -> bool:
    return bool(detect_uv_info().get("installed"))


def evaluate_marker(condition_text: str) -> bool:
    marker = Marker(condition_text)
    return marker.evaluate(default_environment())


def parse_odoo_requirements(requirements_path: str) -> list[str]:
    packages = ["wheel"]
    with open(requirements_path) as requirements_file:
        for line in requirements_file.readlines():
            data = line.split(";")
            if len(data) == 1:
                package = data[0].split("#")[0].strip()
                if package:
                    packages.append(package)
                continue
            package_version, condition_text = data
            condition_text = condition_text.split("#")[0].strip()
            if evaluate_marker(condition_text):
                packages.append(package_version.strip())
    return packages


def _make_pip_runner(spec: VenvInstallSpec, use_uv: bool) -> PipRunner:
    venv_python = venv_python_path(spec.venv_dir)
    if use_uv:
        return PipRunner(
            base_cmd=["uv"],
            pip_extra_args=[*UV_PIP_INSTALL_OPTIONS, "--python", venv_python],
            cwd=spec.project_dir,
        )
    return PipRunner(
        base_cmd=[venv_python, "-m"],
        pip_extra_args=[],
        cwd=spec.project_dir,
    )


def _run_subprocess(cmd: list[str], *, cwd: str) -> None:
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        rendered = " ".join(cmd)
        _logger.error("Command failed (exit %s): %s", result.returncode, rendered)
        raise VenvError(
            f"Command failed (exit {result.returncode}): {rendered}",
            exit_code=result.returncode,
        )


def run_pip_command(
    command: str | list[str],
    *,
    cwd: str | None = None,
    venv_dir: str | None = None,
) -> None:
    """Run a pip/uv argv list (or legacy shell-less string) for callers outside bake."""
    argv = shlex.split(command) if isinstance(command, str) else list(command)
    workdir = cwd if cwd is not None else os.getcwd()
    if venv_dir is not None:
        apply_venv_env(venv_dir)
    _run_subprocess(argv, cwd=workdir)


def create_venv(spec: VenvInstallSpec, use_uv: bool) -> None:
    if not use_uv:
        env = venv.EnvBuilder(with_pip=True)
        env.create(spec.venv_dir)
        return
    result = subprocess.run(
        ["uv", "venv", spec.venv_dir, "--python", sys.executable],
        cwd=spec.project_dir,
        check=False,
    )
    if result.returncode != 0:
        message = f"uv venv failed (exit {result.returncode})"
        _logger.error(message)
        raise VenvError(message, exit_code=result.returncode)


def activate_venv(spec: VenvInstallSpec) -> None:
    activate_path = _find_file(spec.venv_dir, "activate")
    if not activate_path:
        message = f"activate script not found under {spec.venv_dir}"
        _logger.error(message)
        raise VenvError(message)
    apply_venv_env(spec.venv_dir, python_version=spec.python_version)


def _find_file(start_dir: str, pattern: str) -> str:
    for root, _dirs, files in os.walk(start_dir):
        for name in files:
            if pattern in name:
                return os.path.join(root, name)
    return ""


def bootstrap_packages(spec: VenvInstallSpec, pip: PipRunner) -> None:
    for package in resolve_bootstrap_packages(spec):
        pip.install(package)


def install_odoo_requirement_packages(
    packages: list[str],
    pip: PipRunner,
    requirements_path: str,
) -> None:
    for package in packages:
        if "gevent" in package:
            pip.install_gevent(package)
    pip.install_requirements(requirements_path)
    for package in constants.ODOO_VENV_IMPLICIT_PACKAGES:
        pip.install(package)


def install_extra_packages(extra_packages: list[str], pip: PipRunner) -> None:
    for package in extra_packages:
        package = package.strip()
        if package:
            pip.install(package)


def install_fresh(
    spec: VenvInstallSpec,
    *,
    use_uv: bool | None = None,
    lock_file_path: str | None = None,
    lock_hash: str | None = None,
) -> None:
    if use_uv is None:
        use_uv = detect_uv()
    pip = _make_pip_runner(spec, use_uv)
    create_venv(spec, use_uv)
    activate_venv(spec)
    odoo_packages = parse_odoo_requirements(spec.odoo_requirements_path)
    bootstrap_packages(spec, pip)
    install_odoo_requirement_packages(
        odoo_packages, pip, spec.odoo_requirements_path
    )
    install_extra_packages(spec.extra_packages, pip)
    if lock_file_path and lock_hash is not None:
        with open(lock_file_path, "w") as lock_file:
            lock_file.write(lock_hash)


def build_spec_from_config(config: ContainerConfig) -> VenvInstallSpec:
    odoo_requirements_path = os.path.join(
        config.docker_odoo_dir, "requirements.txt"
    )
    return VenvInstallSpec(
        project_dir=config.docker_project_dir,
        venv_dir=config.docker_venv_dir,
        odoo_requirements_path=odoo_requirements_path,
        extra_packages=list(config.requirements_txt),
        python_version=config.python_version,
        bootstrap_packages=get_venv_bootstrap_packages(config.python_version),
    )


def write_ci_venv_install_spec(context_dir: str, spec: VenvInstallSpec) -> str:
    config_path = os.path.join(context_dir, constants.CI_VENV_INSTALL_JSON)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as config_file:
        json.dump(spec.to_dict(), config_file, indent=2, ensure_ascii=False)
        config_file.write("\n")
    return config_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Install Odoo virtualenv (CI bake)")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to venv_install.json (VenvInstallSpec)",
    )
    args = parser.parse_args(argv)
    try:
        spec = VenvInstallSpec.from_json_file(args.config)
        install_fresh(
            spec,
            lock_file_path=spec.lock_file_path,
            lock_hash=spec.lock_hash,
        )
    except VenvError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
