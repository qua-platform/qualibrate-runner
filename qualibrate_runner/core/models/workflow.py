from typing import Optional

from pydantic import BaseModel

from qualibrate_runner.core.models.last_run import RunError, RunStatus


class WorkflowStatus(BaseModel):
    active: bool
    status: RunStatus
    active_node_name: Optional[str]
    nodes_completed: int
    nodes_total: int
    run_duration: float
    error: Optional[RunError] = None
