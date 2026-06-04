import asyncio
import logging
import re

from django.conf import settings

from config.celery import app as celery_app
from apps.executions.models import Execution
from .engine import WorkflowEngine

logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """Convert Markdown-formatted AI output to clean plain text for Telegram.

    Handles the most common patterns produced by LLMs:
      - Fenced code blocks  (``` ... ```)
      - Inline code         (`code`)
      - ATX headers         (### Title)
      - Bold/italic         (**text**, *text*, __text__, _text_)
      - Unordered bullets   (- item, * item)
      - Ordered bullets     (1. item)
      - Horizontal rules    (---)
      - Extra blank lines   (collapses 3+ newlines to 2)
    """
    # 1. Remove fenced code blocks, keep the inner text
    text = re.sub(r"```[\w]*\n?(.*?)```", r"\1", text, flags=re.DOTALL)
    # 2. Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 3. Strip ATX headers — keep the title text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 4. Bold+italic (***text***)
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    # 5. Bold (**text** or __text__)
    text = re.sub(r"(\*{2}|_{2})(.+?)\1", r"\2", text)
    # 6. Italic (*text* or _text_)
    text = re.sub(r"(\*|_)(.+?)\1", r"\2", text)
    # 7. Bullet list markers  (- , * , + ) — keep the content
    text = re.sub(r"^[\-\*\+]\s+", "", text, flags=re.MULTILINE)
    # 8. Ordered list markers (1. , 2. , etc.)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # 9. Horizontal rules
    text = re.sub(r"^[-_*]{3,}\s*$", "", text, flags=re.MULTILINE)
    # 10. Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_workflow(self, execution_id: int):
    """Celery task that runs a workflow execution asynchronously.

    Uses asyncio.run() since WorkflowEngine uses async LLM calls.
    Retries up to 3 times on transient failures.
    """
    logger.info("Celery task started for execution %s", execution_id)

    try:

        async def _run():
            engine = WorkflowEngine()
            await engine.run(execution_id)

        asyncio.run(_run())
        logger.info("Celery task completed for execution %s", execution_id)

        _send_telegram_response(execution_id)

    except Exception as exc:
        logger.exception("Execution %s failed in Celery task", execution_id)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Execution %s exhausted retries", execution_id)
            Execution.objects.filter(id=execution_id).update(
                status=Execution.Status.FAILED,
                error_message=str(exc),
            )


def _send_telegram_response(execution_id: int):
    execution = Execution.objects.select_related("workflow").filter(id=execution_id).first()
    if not execution:
        return

    chat_id = (execution.input_data or {}).get("telegram_chat_id")
    if not chat_id:
        return

    from apps.telegram.actions import send_telegram_message_sync

    status = execution.status
    workflow_name = execution.workflow.name

    if status == Execution.Status.COMPLETED:
        output = execution.output_data or {}
        text = output.get("content") or output.get("result")
        
        if not text:
            node_results = output.get("node_results", {})
            if node_results:
                last_node_id = None
                if execution.workflow and getattr(execution.workflow, "nodes", None):
                    for node in reversed(execution.workflow.nodes):
                        nid = node.get("id")
                        if nid in node_results:
                            last_node_id = nid
                            break
                if not last_node_id:
                    last_node_id = list(node_results.keys())[-1]

                final_text = node_results[last_node_id]
                # Strip Markdown formatting so Telegram displays clean plain text.
                clean_text = _strip_markdown(final_text)
                text = (
                    f"\u2728 Workflow Completed!\n\n"
                    f"Workflow: {workflow_name}\n"
                    f"Execution ID: {execution_id}\n\n"
                    f"{clean_text}"
                )
            else:
                text = (
                    f"\u2728 Workflow Completed!\n\n"
                    f"Workflow: {workflow_name}\n"
                    f"Execution ID: {execution_id}\n\n"
                    f"No step results were recorded."
                )
    elif status == Execution.Status.FAILED:
        error_msg = execution.error_message or "An unexpected error occurred during execution."
        text = (
            f"❌ *Workflow Execution Failed*\n\n"
            f"*Workflow:* {workflow_name}\n"
            f"*Execution ID:* `{execution_id}`\n\n"
            f"*Error:* {error_msg}"
        )
    elif status == Execution.Status.CANCELLED:
        text = (
            f"⏹️ *Workflow Cancelled*\n\n"
            f"*Workflow:* {workflow_name}\n"
            f"*Execution ID:* `{execution_id}`"
        )
    elif status == Execution.Status.NEEDS_APPROVAL:
        text = (
            f"⚠️ *Workflow Awaiting Approval*\n\n"
            f"*Workflow:* {workflow_name}\n"
            f"*Execution ID:* `{execution_id}`\n\n"
            f"This workflow requires human approval to proceed. Please check the dashboard."
        )
    else:
        text = (
            f"ℹ️ *Workflow Status Update*\n\n"
            f"*Workflow:* {workflow_name}\n"
            f"*Execution ID:* `{execution_id}`\n"
            f"*Status:* {status.upper()}"
        )

    # Send as plain text to avoid Markdown parse errors from AI-generated content
    send_telegram_message_sync(chat_id, text, parse_mode=None)
