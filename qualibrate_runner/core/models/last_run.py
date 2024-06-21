from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, Field


class RunStatus(Enum):
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class RunError(BaseModel):
    error_class: str
    message: str
    traceback: list[str]


class LastRun(BaseModel):
    status: RunStatus
    name: str
    idx: int
    state_updates: Mapping[str, Any] = Field(default_factory=dict)
    error: Optional[RunError] = None
