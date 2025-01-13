import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from qualibrate_config.file import get_config_file
from qualibrate_config.models import CalibrationLibraryConfig
from qualibrate_config.resolvers import get_qualibrate_config

from qualibrate_runner.config.vars import (
    CONFIG_PATH_ENV_NAME,
    DEFAULT_QUALIBRATE_RUNNER_CONFIG_FILENAME,
)

__all__ = ["get_config_path", "get_settings"]


@lru_cache
def get_config_path() -> Path:
    return get_config_file(
        config_path=os.environ.get(CONFIG_PATH_ENV_NAME),
        default_config_specific_filename=DEFAULT_QUALIBRATE_RUNNER_CONFIG_FILENAME,
        raise_not_exists=True,
    )


@lru_cache
def get_settings(
    config_path: Annotated[Path, Depends(get_config_path)],
) -> CalibrationLibraryConfig:
    q_config = get_qualibrate_config(config_path)
    q_lib = q_config.calibration_library
    if q_lib is None:
        raise ValueError("Calibration library is not specified in config")
    return q_lib
