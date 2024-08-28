import traceback
from typing import Any, Mapping, Type

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from qualibrate.qualibration_graph import QualibrationGraph
from qualibrate.qualibration_library import QualibrationLibrary
from qualibrate.qualibration_node import QualibrationNode

from qualibrate_runner.config import State
from qualibrate_runner.core.models.last_run import LastRun, RunError, RunStatus


def validate_input_parameters(
    parameters_class: Type[BaseModel],
    passed_parameters: Mapping[str, Any],
) -> BaseModel:
    try:
        return parameters_class.model_validate(passed_parameters)
    except ValidationError as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=ex.errors()
        )


def run_node(
    node: QualibrationNode,
    passed_input_parameters: Mapping[str, Any],
    state: State,
) -> None:
    state.passed_parameters = passed_input_parameters
    state.run_item = node
    state.last_run = LastRun(
        name=node.name,
        status=RunStatus.RUNNING,
        idx=-1,
    )
    try:
        library = QualibrationLibrary.active_library
        node = library.nodes[node.name]
        result = library.run_node(
            node.name, node.parameters_class(**passed_input_parameters)
        )
    except Exception as ex:
        state.last_run = LastRun(
            name=state.last_run.name,
            status=RunStatus.ERROR,
            idx=-1,
            error=RunError(
                error_class=ex.__class__.__name__,
                message=str(ex),
                traceback=traceback.format_tb(ex.__traceback__),
            ),
        )
        raise
    else:
        idx = node.snapshot_idx if hasattr(node, "snapshot_idx") else -1
        idx = idx if idx is not None else -1
        state.last_run = LastRun(
            name=state.last_run.name,
            status=RunStatus.FINISHED,
            idx=idx,
            run_result=result,
            state_updates=node.state_updates,
        )


def run_workflow(
    workflow: QualibrationGraph,
    passed_input_parameters: Mapping[str, Any],
    state: State,
) -> None:
    state.passed_parameters = passed_input_parameters
    state.last_run = LastRun(
        name=workflow.name,
        status=RunStatus.RUNNING,
        idx=-1,
    )
    state.run_item = workflow
    try:
        library = QualibrationLibrary.active_library
        workflow = library.graphs[workflow.name]
        result = library.run_graph(
            workflow.name,
            workflow.full_parameters_class(**passed_input_parameters),
        )
        print("Graph completed. Result:", result)
    except Exception as ex:
        state.last_run = LastRun(
            name=state.last_run.name,
            status=RunStatus.ERROR,
            idx=-1,
            error=RunError(
                error_class=ex.__class__.__name__,
                message=str(ex),
                traceback=traceback.format_tb(ex.__traceback__),
            ),
        )
        raise
    else:
        idx = workflow.snapshot_idx if hasattr(workflow, "snapshot_idx") else -1
        idx = idx if idx is not None else -1
        state.last_run = LastRun(
            name=state.last_run.name,
            status=RunStatus.FINISHED,
            idx=idx,
            run_result=result,
            state_updates=(
                workflow.state_updates
                if hasattr(workflow, "state_updates")
                else {}
            ),
        )
