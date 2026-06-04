import asyncio
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.workflows.models import Workflow
from apps.executions.models import Execution, ExecutionNode
from .graph import build_and_compile
from .state import WorkflowState
from apps.executions.notifications import (
    notify_execution_started,
    notify_execution_completed,
    notify_execution_failed,
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates async workflow execution using LangGraph.

    Takes an Execution, builds a LangGraph graph from the workflow definition,
    runs it, and persists results back to the database.
    """

    async def run(self, execution_id: int) -> None:
        execution = await _get_execution(execution_id)
        workflow = await _get_workflow(execution.workflow_id)

        logger.info("Starting execution %s for workflow %s", execution_id, workflow.name)
        await notify_execution_started(execution_id, workflow.name, execution.input_data or {})

        await _ensure_execution_nodes(execution, workflow)

        graph = build_and_compile(workflow)

        paused_state = None
        if execution.status == Execution.Status.NEEDS_APPROVAL and execution.output_data:
            paused_state = execution.output_data.get("_paused_state")

        initial_state: WorkflowState = {
            "execution_id": execution_id,
            "messages": (paused_state or {}).get("messages", []),
            "node_results": (paused_state or {}).get("node_results", {}),
            "completed_nodes": (paused_state or {}).get("completed_nodes", []),
            "input_data": execution.input_data or {},
            "output_data": (paused_state or {}).get("output_data", {}),
            "status": "running",
            "error": "",
            "raw_text": (paused_state or {}).get("raw_text", ""),
            "sections": (paused_state or {}).get("sections", {}),
            "extracted_skills": (paused_state or {}).get("extracted_skills", {}),
            "extracted_experience": (paused_state or {}).get("extracted_experience", []),
            "extracted_education": (paused_state or {}).get("extracted_education", []),
            "pipeline_score": (paused_state or {}).get("pipeline_score", {}),
            "pipeline_output": (paused_state or {}).get("pipeline_output", []),
        }

        try:
            final_state = await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": str(execution_id)}},
            )

            if final_state.get("status") == "failed":
                logger.error("Execution %s failed: %s", execution_id, final_state.get("error"))
                await notify_execution_failed(execution_id, final_state.get("error", "unknown"))
                return

            if final_state.get("status") == "needs_approval":
                logger.info("Execution %s paused — awaiting human approval", execution_id)
                await sync_to_async(_mark_execution_paused)(execution_id, final_state)
                return

            output_data = final_state.get("output_data") or _build_output(final_state)
            await sync_to_async(_mark_execution_completed)(execution_id, output_data)
            await notify_execution_completed(execution_id, output_data)

            logger.info("Execution %s completed successfully", execution_id)

        except Exception as e:
            logger.exception("Execution %s crashed: %s", execution_id, e)
            await sync_to_async(_mark_execution_crashed)(execution_id, str(e))
            await notify_execution_failed(execution_id, str(e))


def _build_output(state: WorkflowState) -> dict:
    return {
        "node_results": state.get("node_results", {}),
        "messages": state.get("messages", []),
        "raw_text": state.get("raw_text", ""),
        "sections": state.get("sections", {}),
        "extracted_skills": state.get("extracted_skills", {}),
        "extracted_experience": state.get("extracted_experience", []),
        "extracted_education": state.get("extracted_education", []),
        "pipeline_score": state.get("pipeline_score", {}),
        "pipeline_output": state.get("pipeline_output", []),
    }


async def _ensure_execution_nodes(execution: Execution, workflow: Workflow):
    from apps.agents.models import Agent
    existing = await sync_to_async(
        lambda: list(ExecutionNode.objects.filter(execution=execution).values_list("node_id", flat=True))
    )()
    existing_set = set(existing)

    to_create = []
    for node in workflow.nodes:
        nid = node["id"]
        if nid in existing_set:
            continue
        agent_id = node.get("agentId") or node.get("data", {}).get("agentId")
        agent = await sync_to_async(Agent.objects.filter(id=agent_id).first)() if agent_id else None
        to_create.append(ExecutionNode(
            execution=execution,
            node_id=nid,
            agent=agent,
            status=Execution.Status.PENDING,
            input_data=execution.input_data or {},
        ))

    if to_create:
        await sync_to_async(ExecutionNode.objects.bulk_create)(to_create)
        logger.info("Created %d ExecutionNode records for execution %s", len(to_create), execution.id)


async def _get_execution(execution_id: int) -> Execution:
    from asgiref.sync import sync_to_async
    return await sync_to_async(Execution.objects.select_related("workflow").get)(id=execution_id)


async def _get_workflow(workflow_id: int) -> Workflow:
    from asgiref.sync import sync_to_async
    return await sync_to_async(Workflow.objects.get)(id=workflow_id)


def _mark_execution_completed(execution_id: int, output_data: dict):
    Execution.objects.filter(id=execution_id).update(
        status=Execution.Status.COMPLETED,
        output_data=output_data,
        completed_at=timezone.now(),
    )


def _mark_execution_crashed(execution_id: int, error: str):
    Execution.objects.filter(id=execution_id).update(
        status=Execution.Status.FAILED,
        error_message=error,
        completed_at=timezone.now(),
    )


def _mark_execution_paused(execution_id: int, state: dict):
    output_data = {"_paused_state": state}
    node_results = state.get("node_results", {})
    node_ids = list(node_results.keys())
    if node_ids:
        last_key = node_ids[-1]
        output_data["content"] = node_results[last_key][:2000] if node_results[last_key] else ""
    Execution.objects.filter(id=execution_id).update(
        status=Execution.Status.NEEDS_APPROVAL,
        output_data=output_data,
    )
