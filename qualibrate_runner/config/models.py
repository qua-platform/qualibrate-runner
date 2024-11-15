from pathlib import Path
from typing import Callable, Optional, Union

from pydantic import BaseModel, ConfigDict, DirectoryPath, ImportString
from pydantic_settings import SettingsConfigDict
from qualibrate.qualibration_graph import QualibrationGraph
from qualibrate.qualibration_library import QualibrationLibrary
from qualibrate.qualibration_node import QualibrationNode
from qualibrate_config.models.base.base_referenced_settings import (
    BaseReferencedSettings,
)

from qualibrate_runner.config.vars import Q_RUNNER_SETTINGS_ENV_PREFIX
from qualibrate_runner.core.models.last_run import LastRun, RunStatus


class State(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    last_run: Optional[LastRun] = None
    run_item: Optional[Union[QualibrationNode, QualibrationGraph]] = None

    @property
    def is_running(self) -> bool:
        return (
            self.last_run is not None
            and self.last_run.status == RunStatus.RUNNING
        )


class QualibrateRunnerSettings(BaseReferencedSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        env_prefix=Q_RUNNER_SETTINGS_ENV_PREFIX,
    )

    calibration_library_resolver: ImportString[
        Callable[[Path], QualibrationLibrary]
    ]
    calibration_library_folder: DirectoryPath
