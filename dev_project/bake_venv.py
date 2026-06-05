"""Shared virtualenv installation for dev container and CI image bake."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from dataclasses import asdict, dataclass, field
from typing import Any

from pip._vendor.packaging.markers import Marker, default_environment

try:
    from . import constants
except ImportError:
    constants = None  # type: ignore[assignment]

try:
    from .inside_docker_app.logger import get_module_logger
except ImportError:
    from logger import get_module_logger


_logger = get_module_logger(__name__)

_FALLBACK_BOOTSTRAP = ["cython<3.0", "wheel", "setuptools"]

UV_PIP_OPTIONS = "--link-mode=copy"


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


def get_venv_bootstrap_packages(python_version: str) -> list[str]:
    if constants is None:
        return list(_FALLBACK_BOOTSTRAP)
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


def _pip_manager(use_uv: bool) -> tuple[str, str]:
    if use_uv:
        return "uv", UV_PIP_OPTIONS
    return "python3 -m", ""


def run_pip_command(command: str) -> None:
    result = subprocess.run([command], shell=True)
    if result.returncode != 0:
        _logger.error("Command failed (exit %s): %s", result.returncode, command)
        sys.exit(1)


def create_venv(spec: VenvInstallSpec, use_uv: bool) -> None:
    if not use_uv:
        env = venv.EnvBuilder(with_pip=True)
        env.create(spec.venv_dir)
        return
    result = subprocess.run(
        ["uv", "venv", spec.venv_dir],
        cwd=spec.project_dir,
        check=False,
    )
    if result.returncode != 0:
        _logger.error("uv venv failed (exit %s)", result.returncode)
        sys.exit(1)


def activate_venv(spec: VenvInstallSpec) -> None:
    activate_path = _find_file(spec.venv_dir, "activate")
    if not activate_path:
        _logger.error("activate script not found under %s", spec.venv_dir)
        sys.exit(1)
    venv_bin_dir = os.path.dirname(activate_path)
    venv_lib_path = os.path.join(
        spec.venv_dir, "lib", f"python{spec.python_version}", "site-packages"
    )
    os.environ["PATH"] = venv_bin_dir + os.pathsep + os.environ["PATH"]
    sys.path.insert(1, venv_lib_path)


def _find_file(start_dir: str, pattern: str) -> str:
    for root, _dirs, files in os.walk(start_dir):
        for name in files:
            if pattern in name:
                return os.path.join(root, name)
    return ""


def bootstrap_packages(
    spec: VenvInstallSpec, manager_command: str, options: str
) -> None:
    for package in resolve_bootstrap_packages(spec):
        run_pip_command(
            f'{manager_command} pip install "{package}" {options}'.strip()
        )


def install_odoo_requirement_packages(
    packages: list[str],
    manager_command: str,
    options: str,
    requirements_path: str,
) -> None:
    for package in packages:
        if "gevent" in package:
            gevent_spec = f"{package} --no-build-isolation"
            gevent_spec = gevent_spec.replace("<", "=").replace(">", "=")
            run_pip_command(
                f"{manager_command} pip install {gevent_spec} {options}".strip()
            )
    run_pip_command(
        f"{manager_command} pip install -r {requirements_path} {options}".strip()
    )


def install_extra_packages(
    extra_packages: list[str], manager_command: str, options: str
) -> None:
    for package in extra_packages:
        package = package.strip()
        if not package:
            continue
        run_pip_command(
            f"{manager_command} pip install {package} {options}".strip()
        )


def install_fresh(
    spec: VenvInstallSpec,
    *,
    use_uv: bool | None = None,
    lock_file_path: str | None = None,
    lock_hash: str | None = None,
) -> None:
    if use_uv is None:
        use_uv = detect_uv()
    os.chdir(spec.project_dir)
    manager_command, options = _pip_manager(use_uv)
    create_venv(spec, use_uv)
    activate_venv(spec)
    odoo_packages = parse_odoo_requirements(spec.odoo_requirements_path)
    bootstrap_packages(spec, manager_command, options)
    install_odoo_requirement_packages(
        odoo_packages,
        manager_command,
        options,
        spec.odoo_requirements_path,
    )
    install_extra_packages(spec.extra_packages, manager_command, options)
    if lock_file_path and lock_hash is not None:
        with open(lock_file_path, "w") as lock_file:
            lock_file.write(lock_hash)


def build_spec_from_config(config: dict[str, Any]) -> VenvInstallSpec:
    odoo_requirements_path = os.path.join(
        config["docker_odoo_dir"], "requirements.txt"
    )
    return VenvInstallSpec(
        project_dir=config["docker_project_dir"],
        venv_dir=config.get("docker_venv_dir", ""),
        odoo_requirements_path=odoo_requirements_path,
        extra_packages=list(config.get("requirements_txt") or []),
        python_version=config["python_version"],
        bootstrap_packages=get_venv_bootstrap_packages(config["python_version"]),
    )


def write_ci_bake_dir(
    context_dir: str, spec: VenvInstallSpec, dev_project_dir: str
) -> str:
    if constants is None:
        raise RuntimeError("write_ci_bake_dir must run from the dev_project package")
    bake_dir = os.path.join(context_dir, constants.CI_BAKE_DIR)
    os.makedirs(bake_dir, exist_ok=True)
    for rel_path in constants.CI_BAKE_PYTHON_FILES:
        src = os.path.join(dev_project_dir, rel_path)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"CI bake module not found: {src}")
        dest = os.path.join(bake_dir, os.path.basename(rel_path))
        shutil.copy2(src, dest)
    config_path = os.path.join(bake_dir, constants.CI_VENV_INSTALL_JSON)
    with open(config_path, "w") as config_file:
        json.dump(spec.to_dict(), config_file, indent=2, ensure_ascii=False)
        config_file.write("\n")
    return bake_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Install Odoo virtualenv (CI bake)")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to venv_install.json (VenvInstallSpec)",
    )
    args = parser.parse_args(argv)
    spec = VenvInstallSpec.from_json_file(args.config)
    install_fresh(
        spec,
        lock_file_path=spec.lock_file_path,
        lock_hash=spec.lock_hash,
    )


if __name__ == "__main__":
    main()
