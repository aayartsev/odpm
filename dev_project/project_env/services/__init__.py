from .docker_base_image import BaseImageService
from .pycharm_configurator import PycharmConfigurator
from .python_analysis_paths import PythonAnalysisPathsBuilder
from .vscode_configurator import VscodeConfigurator

__all__ = [
    "BaseImageService",
    "CiImageBuildService",
    "PycharmConfigurator",
    "PythonAnalysisPathsBuilder",
    "VscodeConfigurator",
]


def __getattr__(name: str):
    if name == "CiImageBuildService":
        from .ci_image_build import CiImageBuildService

        return CiImageBuildService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
