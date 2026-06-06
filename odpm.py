#!/bin/python3
import os
import sys

import dev_project.translations as translations
from dev_project.logging import get_module_logger
from dev_project.inside_docker_app.parse_args import parse_args
from dev_project.odpm_pipeline import OdpmPipeline

_logger = get_module_logger(__name__)

if hasattr(os, "geteuid") and os.geteuid() == 0:
    _logger.error(translations.get_translation(translations.RUNNING_AS_ROOT_DISABLED))
    sys.exit(1)


def main() -> None:
    program_dir_path = os.path.dirname(os.path.abspath(__file__))
    OdpmPipeline(parse_args(), program_dir_path).run()


if __name__ == "__main__":
    main()
