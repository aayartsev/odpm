#!/usr/bin/env python3

import os

from dev_project.cli import main

if __name__ == "__main__":
    main(program_dir=os.path.dirname(os.path.abspath(__file__)))
