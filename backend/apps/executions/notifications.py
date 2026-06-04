import logging

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def notify_execution_event(execution_id: int, event_type: str, data: dict) -> None:
    """Persist an execution event to the database for SSE clients to poll."""
    try:
        from apps.executions.models import ExecutionEvent
        await sync_to_async(ExecutionEvent.objects.create)(
            execution_id=execution_id,
            event_type=event_type,
            data=data,
        )
    except Exception:
        logger.exception("Failed to persist event for execution %s", execution_id)


async def notify_node_status(execution_id: int, node_id: str, status: str, **extra) -> None:
    await notify_execution_event(
        execution_id,
        "node.status",
        {
            "execution_id": execution_id,
            "node_id": node_id,
            "status": status,
            **extra,
        },
    )


async def notify_execution_started(execution_id: int, workflow_name: str, input_data: dict) -> None:
    await notify_execution_event(
        execution_id,
        "execution.started",
        {
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "input_data": input_data,
        },
    )


async def notify_execution_completed(execution_id: int, output_data: dict) -> None:
    await notify_execution_event(
        execution_id,
        "execution.completed",
        {
            "execution_id": execution_id,
            "output_data": output_data,
        },
    )


async def notify_execution_failed(execution_id: int, error: str) -> None:
    await notify_execution_event(
        execution_id,
        "execution.failed",
        {
            "execution_id": execution_id,
            "error": error,
        },
    )


async def notify_execution_approved(execution_id: int, approved: bool, feedback: str) -> None:
    await notify_execution_event(
        execution_id,
        "execution.approved",
        {
            "execution_id": execution_id,
            "approved": approved,
            "feedback": feedback,
        },
    )


async def notify_message_created(
    execution_id: int, node_id: str, agent_name: str, role: str, content: str, token_count: int
) -> None:
    await notify_execution_event(
        execution_id,
        "message.created",
        {
            "execution_id": execution_id,
            "node_id": node_id,
            "agent_name": agent_name,
            "role": role,
            "content": content,
            "token_count": token_count,
        },
    )
