import logging
import traceback
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Optional, cast

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from qualibrate.models.run_summary.graph import GraphRunSummary
from qualibrate.models.run_summary.node import NodeRunSummary
from qualibrate.qualibration_library import QualibrationLibrary

from qualibrate_runner.config import State
from qualibrate_runner.core.models.common import RunError
from qualibrate_runner.core.models.enums import RunnableType, RunStatusEnum
from qualibrate_runner.core.models.last_run import LastRun
from qualibrate_runner.core.types import QGraphType, QLibraryType, QNodeType

logger = logging.getLogger(__name__)


def validate_input_parameters(
    parameters_class: type[BaseModel],
    passed_parameters: Mapping[str, Any],
) -> BaseModel:
    try:
        return parameters_class.model_validate(passed_parameters)
    except ValidationError as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=ex.errors()
        ) from ex


def get_active_library_or_error() -> QLibraryType:
    return QualibrationLibrary.get_active_library(create=False)


def run_node(
    node: QNodeType,
    passed_input_parameters: Mapping[str, Any],
    state: State,
) -> None:
    state.run_item = node
    run_status = RunStatusEnum.RUNNING
    state.last_run = LastRun(
        name=node.name,
        status=RunStatusEnum.RUNNING,
        idx=-1,
        passed_parameters=passed_input_parameters,
        started_at=datetime.now().astimezone(),
        runnable_type=RunnableType.NODE,
    )
    idx = -1
    run_error = None
    try:
        node.run(interactive=True, **passed_input_parameters)
    except Exception as ex:
        run_status = RunStatusEnum.ERROR
        run_error = RunError(
            error_class=ex.__class__.__name__,
            message=str(ex),
            traceback=traceback.format_tb(ex.__traceback__),
        )
        raise
    else:
        _idx = node.snapshot_idx if hasattr(node, "snapshot_idx") else -1
        idx = _idx if _idx is not None else -1
        run_status = RunStatusEnum.FINISHED
    finally:
        state.last_run = LastRun(
            name=state.last_run.name,
            status=run_status,
            idx=idx,
            # TODO: Make run summary generic
            run_result=cast(Optional[NodeRunSummary], node.run_summary),
            runnable_type=state.last_run.runnable_type,
            passed_parameters=passed_input_parameters,
            started_at=state.last_run.started_at,
            completed_at=datetime.now().astimezone(),
            state_updates=node.state_updates,
            error=run_error,
        )


def run_workflow(
    workflow: QGraphType,
    passed_input_parameters: Mapping[str, Any],
    state: State,
) -> None:
    logger.info(f"🔵 WORKFLOW_DEBUG: Starting background task for workflow '{workflow.name}'")
    logger.info(f"🔵 WORKFLOW_DEBUG: Background task received parameters: {passed_input_parameters}")
    
    run_status = RunStatusEnum.RUNNING
    state.last_run = LastRun(
        name=workflow.name,
        status=run_status,
        idx=-1,
        started_at=datetime.now().astimezone(),
        runnable_type=RunnableType.GRAPH,
        passed_parameters=passed_input_parameters,
    )
    logger.info(f"🔵 WORKFLOW_DEBUG: Set initial state to RUNNING")
    
    idx = -1
    run_error = None
    try:
        logger.info(f"🔵 WORKFLOW_DEBUG: Getting active library...")
        library = get_active_library_or_error()
        logger.info(f"🔵 WORKFLOW_DEBUG: ✅ Got library, getting workflow '{workflow.name}'")
        
        workflow = library.graphs[workflow.name]  # copied graph instance
        state.run_item = workflow
        logger.info(f"🔵 WORKFLOW_DEBUG: ✅ Got workflow copy, parameters class: {workflow.full_parameters_class}")
        
        # THIS IS THE CRITICAL VALIDATION STEP THAT MIGHT FAIL
        logger.info(f"🔵 WORKFLOW_DEBUG: Starting background task parameter validation...")
        try:
            input_parameters = workflow.full_parameters_class(
                **passed_input_parameters
            )
            logger.info(f"🔵 WORKFLOW_DEBUG: ✅ Background validation passed, created input_parameters")
        except Exception as validation_ex:
            logger.error(f"🔵 WORKFLOW_DEBUG: ❌ BACKGROUND VALIDATION FAILED: {type(validation_ex).__name__}: {validation_ex}")
            logger.error(f"🔵 WORKFLOW_DEBUG: Validation error details: {getattr(validation_ex, 'errors', 'No error details')}")
            raise validation_ex
        
        logger.info(f"🔵 WORKFLOW_DEBUG: Starting workflow.run() execution...")
        workflow.run(
            nodes=input_parameters.nodes.model_dump(),
            **input_parameters.parameters.model_dump(),
        )
        logger.info(f"🔵 WORKFLOW_DEBUG: ✅ workflow.run() completed successfully")
        
    except Exception as ex:
        logger.error(f"🔵 WORKFLOW_DEBUG: ❌ EXCEPTION IN BACKGROUND TASK: {type(ex).__name__}: {ex}")
        logger.error(f"🔵 WORKFLOW_DEBUG: Full traceback: {''.join(traceback.format_tb(ex.__traceback__))}")
        
        run_status = RunStatusEnum.ERROR
        run_error = RunError(
            error_class=ex.__class__.__name__,
            message=str(ex),
            traceback=traceback.format_tb(ex.__traceback__),
        )
        logger.error(f"🔵 WORKFLOW_DEBUG: Created RunError, re-raising exception")
        raise
    else:
        idx = workflow.snapshot_idx if hasattr(workflow, "snapshot_idx") else -1
        idx = idx if idx is not None else -1
        run_status = RunStatusEnum.FINISHED
        logger.info(f"🔵 WORKFLOW_DEBUG: ✅ Workflow completed successfully, status: FINISHED")
    finally:
        logger.info(f"🔵 WORKFLOW_DEBUG: Updating final state - status: {run_status}, error: {run_error}")
        state.last_run = LastRun(
            name=state.last_run.name,
            status=run_status,
            idx=idx,
            run_result=cast(Optional[GraphRunSummary], workflow.run_summary),
            started_at=state.last_run.started_at,
            completed_at=datetime.now().astimezone(),
            runnable_type=state.last_run.runnable_type,
            passed_parameters=passed_input_parameters,
            error=run_error,
        )
        logger.info(f"🔵 WORKFLOW_DEBUG: Background task completed - final status: {state.last_run.status}")
