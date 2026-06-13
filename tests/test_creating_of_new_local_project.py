#!/usr/bin/env python3
"""
Test script for creating new local Odoo projects.

Creates projects for various Odoo versions, measures execution time and logs results.
"""

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from delete_images import remove_images_by_prefix_cli

CLEAN_ALL_DATA = 0
CLEAN_DOCKER_IMAGES = 0

# Add project root to path for logger import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project.logging import get_module_logger

# Initialize logger from project
_logger = get_module_logger(__name__)

# Odoo versions for testing
ODOO_VERSIONS = ["19.0", "18.0", "17.0", "16.0", "15.0", "14.0", "13.0", "12.0", "11.0"]

# Test paths
TEST_BASE_DIR = Path("/tmp/odoo_test_projects")
BACKUP_DIR = Path("/tmp/odoo_backups")
ODOO_PROJECTS_DIR = Path("/tmp/odoo_projects")


def setup_logging():
    """Configure logging based on project configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cleanup_directory(directory: Path):
    """
    Remove directory contents with elevated privileges.

    Args:
        directory: Path to directory for cleanup
    """
    if directory.exists():
        _logger.info(f"Cleaning directory: {directory}")
        try:
            # Try to remove via shutil
            shutil.rmtree(directory)
        except PermissionError:
            # If failed, use sudo
            _logger.warning(f"sudo required to remove {directory}")
            subprocess.run(
                ["sudo", "rm", "-rf", str(directory)],
                check=True,
                capture_output=True,
            )
        _logger.info(f"Directory {directory} successfully cleaned")


def delete_images():
    os.system("docker builder prune -a -f")
    remove_images_by_prefix_cli("odoo")
    remove_images_by_prefix_cli("python")
    remove_images_by_prefix_cli("postgres")


def create_test_environment(version: str) -> Path:
    """
    Create directory for testing specified Odoo version.

    Args:
        version: Odoo version

    Returns:
        Path to created directory
    """
    version_dir = Path(os.path.join(str(TEST_BASE_DIR), f"test-{version}"))
    if CLEAN_ALL_DATA:
        cleanup_directory(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)
    _logger.info(f"Created directory for version {version}: {version_dir}")
    return version_dir


def create_env_file(work_dir: Path, port_offset: int = 0):
    """
    Create .env file with required parameters.

    Args:
        work_dir: Working directory
        version: Odoo version
        port_offset: Port offset (to avoid conflicts)
    """
    env_content = f"""BACKUP_DIR={BACKUP_DIR}
ODOO_PROJECTS_DIR={ODOO_PROJECTS_DIR}
PATH_TO_SSH_KEY=
ODOO_PORT={9069 + port_offset}
POSTGRES_PORT={6432 + port_offset}
DEBUGGER_PORT={6678 + port_offset}
GEVENT_PORT={9072 + port_offset}
ODPM_SCENARIO=developer
"""
    env_file = work_dir / ".env"
    env_file.write_text(env_content)
    _logger.info(f"Created .env file in {work_dir}")


def run_odpm_script(work_dir: Path, version: str) -> tuple[bool, float]:
    """
    Run odpm.py script for project creation.

    Args:
        work_dir: Working directory
        version: Odoo version

    Returns:
        Tuple (success, elapsed_time)
    """
    odpm_script = PROJECT_ROOT / "odpm.py"

    # Check script existence
    if not odpm_script.exists():
        _logger.error(f"odpm.py script not found: {odpm_script}")
        return False, 0.0

    # Change to working directory
    os.chdir(work_dir)
    _logger.info(f"Changing to working directory: {work_dir}")

    # Measure start time
    start_time = time.time()
    _logger.info(f"Starting execution for version {version}")
    # Build command
    cmd = [
        "python3",
        str(odpm_script),
        "--init",
        ".",
        "--odoo-version",
        version,
        "-d",
        "test_db",
        "--odoo-bin",
        "--stop-after-init",
    ]

    _logger.info(f"Executing command: {' '.join(cmd)}")

    try:
        os.system(f"""{" ".join(cmd)}""")
        elapsed_time = time.time() - start_time
        return True, elapsed_time
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        _logger.error(f"Version {version}: TIMEOUT after {elapsed_time:.2f} sec")
        return False, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        _logger.error(f"Version {version}: EXCEPTION {e} in {elapsed_time:.2f} sec")
        return False, elapsed_time


def cleanup_test_artifacts():
    """
    Remove created test directories after all tests complete successfully.
    """
    if CLEAN_ALL_DATA:
        dirs_to_clean = [TEST_BASE_DIR, BACKUP_DIR, ODOO_PROJECTS_DIR]
        for directory in dirs_to_clean:
            if directory.exists():
                _logger.info(f"Removing test directory: {directory}")
                cleanup_directory(directory)


def main():
    """Main test function."""
    setup_logging()

    _logger.info("=" * 60)
    _logger.info("Starting Odoo project creation testing")
    _logger.info("=" * 60)

    # Dictionary for storing results
    results = {}
    all_success = True
    if CLEAN_DOCKER_IMAGES:
        delete_images()
    try:
        for version in ODOO_VERSIONS:
            _logger.info("-" * 60)
            _logger.info(f"Processing Odoo version: {version}")
            _logger.info("-" * 60)

            # Step 1: Create directory for version
            work_dir = create_test_environment(version)

            # Step 2: Create .env file
            port_offset = ODOO_VERSIONS.index(version) * 10
            create_env_file(work_dir, port_offset)

            # Step 3-6: Run script and get results
            success, elapsed_time = run_odpm_script(work_dir, version)

            # Store results
            results[version] = {
                "success": success,
                "elapsed_time": elapsed_time,
                "work_dir": work_dir,
            }

            if not success:
                all_success = False
                _logger.warning(f"Test for version {version} completed with error")
            else:
                _logger.info(f"Test for version {version} completed successfully")

        # Step 7: Output final results
        _logger.info("=" * 60)
        _logger.info("FINAL RESULTS")
        _logger.info("=" * 60)

        for version, result in results.items():
            status = "✓ SUCCESS" if result["success"] else "✗ ERROR"
            time_str = (
                f"{result['elapsed_time']:.2f} sec"
                if result["elapsed_time"] > 0
                else "N/A"
            )
            _logger.info(f"{version}: {status} | Time: {time_str}")

        if all_success:
            _logger.info("=" * 60)
            _logger.info("All tests completed successfully!")
            _logger.info("Removing test directories...")
            cleanup_test_artifacts()
            _logger.info("Test directories removed")
            _logger.info("=" * 60)
            return 0
        else:
            _logger.warning("Some tests completed with errors")
            _logger.warning("Test directories preserved for debugging")
            return 1

    except KeyboardInterrupt:
        _logger.info("Testing interrupted by user (Control+C)")
        return 1
    except Exception as e:
        _logger.exception(f"Critical error: {e}")
        return 1


if __name__ == "__main__":
    main()
