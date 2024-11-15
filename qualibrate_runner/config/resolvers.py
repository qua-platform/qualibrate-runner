import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from qualibrate_config.file import get_config_file
from qualibrate_config.resolvers import get_config_model
from qualibrate_config.storage import STORAGE

from qualibrate_runner.config.models import QualibrateRunnerSettings
from qualibrate_runner.config.vars import (
    CONFIG_KEY,
    CONFIG_PATH_ENV_NAME,
    DEFAULT_QUALIBRATE_RUNNER_CONFIG_FILENAME,
)

__all__ = [
    "get_config_path",
    "get_settings",
]


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
) -> QualibrateRunnerSettings:
    return get_config_model(
        config_path=config_path,
        config_key=CONFIG_KEY,
        config_model_class=QualibrateRunnerSettings,
        config=STORAGE,
    )
