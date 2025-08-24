import logging
from collections.abc import Mapping
from typing import Annotated, Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from qualibrate_runner.api.dependencies import get_graph_nocopy as get_qgraph
from qualibrate_runner.api.dependencies import get_node_copy as get_qnode_copy
from qualibrate_runner.api.dependencies import (
    get_state,
)
from qualibrate_runner.config import (
    State,
)
from qualibrate_runner.core.run_job import (
    run_node,
    run_workflow,
    validate_input_parameters,
)
from qualibrate_runner.core.types import QGraphType, QNodeType

submit_router = APIRouter(prefix="/submit")
logger = logging.getLogger(__name__)


@submit_router.post("/node")
def submit_node_run(
    input_parameters: Mapping[str, Any],
    state: Annotated[State, Depends(get_state)],
    node: Annotated[QNodeType, Depends(get_qnode_copy)],
    background_tasks: BackgroundTasks,
) -> str:
    # TODO:
    #  this should unify graph submit node params and node submit params
    #  It's needed to correct validation models
    if "parameters" in input_parameters:
        input_parameters = input_parameters["parameters"]
    if state.is_running:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Already running",
        )
    validate_input_parameters(
        cast(type[BaseModel], node.parameters_class), input_parameters
    )
    background_tasks.add_task(run_node, node, input_parameters, state)
    return f"Node job {node.name} is submitted"


@submit_router.post("/workflow")
def submit_workflow_run(
    input_parameters: Mapping[str, Any],
    state: Annotated[State, Depends(get_state)],
    graph: Annotated[QGraphType, Depends(get_qgraph)],
    background_tasks: BackgroundTasks,
) -> str:
    logger.info(f"🟡 GRAPH_DEBUG: Starting workflow submission for graph '{graph.name}'")
    logger.info(f"🟡 GRAPH_DEBUG: Input parameters received: {input_parameters}")
    logger.info(f"🟡 GRAPH_DEBUG: Current state.is_running: {state.is_running}")
    
    if state.is_running:
        logger.warning(f"🟡 GRAPH_DEBUG: Rejected - already running")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Already running",
        )
    
    # Transform parameters
    transformed_parameters = {
        "parameters": input_parameters.get("parameters", {}),
        "nodes": {
            name: params.get("parameters", {})
            for name, params in input_parameters.get("nodes", {}).items()
        },
    }
    logger.info(f"🟡 GRAPH_DEBUG: Transformed parameters: {transformed_parameters}")
    
    # Validation step 1 - main thread
    try:
        logger.info(f"🟡 GRAPH_DEBUG: Starting main thread validation with class: {graph.full_parameters_class}")
        validate_input_parameters(graph.full_parameters_class, transformed_parameters)
        logger.info(f"🟡 GRAPH_DEBUG: ✅ Main thread validation passed")
    except Exception as e:
        logger.error(f"🟡 GRAPH_DEBUG: ❌ Main thread validation failed: {type(e).__name__}: {e}")
        raise
    
    # Add background task
    logger.info(f"🟡 GRAPH_DEBUG: Adding background task for workflow execution")
    background_tasks.add_task(run_workflow, graph, transformed_parameters, state)
    
    success_msg = f"Workflow job {graph.name} is submitted"
    logger.info(f"🟡 GRAPH_DEBUG: ✅ Submission endpoint returning success: {success_msg}")
    return success_msg
