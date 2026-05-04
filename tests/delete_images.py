import logging
import subprocess
import sys
from pathlib import Path
from typing import List

# Add project root to path for logger import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project.inside_docker_app.logger import get_module_logger

# Initialize logger from project
_logger = get_module_logger(__name__)


def setup_logging():
    """Configure logging based on project configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def remove_images_by_prefix_cli(
    prefix: str, force: bool = True, dry_run: bool = False
) -> List[str]:
    """CLI version without installing `docker` package."""
    # Get IDs and tags: \t separation simplifies parsing
    cmd = [
        "docker",
        "images",
        "--filter",
        f"reference={prefix}*",
        "--format",
        "{{.ID}}\t{{.Repository}}:{{.Tag}}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        _logger.error(f"Docker query error: {e.stderr.strip()}")
        return []

    if not lines:
        _logger.info("No images found with specified prefix.")
        return []

    removed = []
    rm_flags = ["-f"] if force else []

    for line in lines:
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        img_id, ref = parts

        if dry_run:
            _logger.info(f"[DRY-RUN] Will be removed: {ref}")
            removed.append(ref)
            continue

        try:
            subprocess.run(
                ["docker", "rmi"] + rm_flags + [img_id],
                check=True,
                capture_output=True,
                text=True,
            )
            _logger.info(f"Removed: {ref}")
            removed.append(ref)
        except subprocess.CalledProcessError as e:
            _logger.error(f"Error removing {ref}: {e.stderr.strip()}")

    return removed
