import logging

from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from asgiref.sync import sync_to_async

from apps.agents.models import Agent
from apps.history.models import Message as HistoryMessage
from apps.telegram.models import TelegramUser
from apps.workflows.models import Workflow
from apps.executions.models import Execution
from llm.schemas import LLMConfig, Message as LLMMessage
from llm.registry import ProviderRegistry

from .actions import send_telegram_message
from runtime.executor import execute_workflow

logger = logging.getLogger(__name__)

_sa = sync_to_async


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _register_user(update)
    await send_telegram_message(
        chat_id,
        "Welcome! I'm your AI agent orchestrator.\n\n"
        "Send me any message to chat.\n"
        "Use /workflows to view pipelines.\n"
        "Use /help for more info.",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await send_telegram_message(
        chat_id,
        "Available commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/workflows - List active workflows\n"
        "/agents - List active agents\n"
        "/executions - List recent executions\n"
        "/workflow <id> <input> - Trigger a workflow\n"
        "/cancel <id> - Cancel a running execution\n\n"
        "Just send a text message to chat with an agent.",
    )


async def workflows_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    workflows = await _sa(lambda: list(Workflow.objects.filter(is_active=True).order_by("id")))()

    if not workflows:
        await send_telegram_message(chat_id, "No active workflows found.")
        return

    msg = "📋 *Active Workflows:*\n\n"
    for wf in workflows:
        msg += f"• *ID: {wf.id}* — {wf.name}\n"
        if wf.description:
            msg += f"  _{wf.description}_\n"

    msg += "\nUse `/workflow <id> <input>` to trigger."
    await send_telegram_message(chat_id, msg, parse_mode="Markdown")


async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    agents = await _sa(lambda: list(Agent.objects.filter(is_active=True).order_by("name")))()

    if not agents:
        await send_telegram_message(chat_id, "No active agents found.")
        return

    msg = "🤖 *Active Agents:*\n\n"
    for agent in agents:
        msg += f"• *{agent.name}* ({agent.role or 'No role'})\n"
        msg += f"  Provider: `{agent.provider}` ({agent.model or 'default'})\n"

    await send_telegram_message(chat_id, msg, parse_mode="Markdown")


async def executions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    executions = await _sa(lambda: list(Execution.objects.select_related("workflow").order_by("-id")[:5]))()

    if not executions:
        await send_telegram_message(chat_id, "No workflow executions found.")
        return

    msg = "⚙️ *Recent Executions:*\n\n"
    for e in executions:
        wf_name = e.workflow.name if e.workflow else "Unknown Workflow"
        status_emoji = "⏳" if e.status == Execution.Status.PENDING else "🔄" if e.status == Execution.Status.RUNNING else "✅" if e.status == Execution.Status.COMPLETED else "❌"
        msg += f"• *#{e.id}* — {wf_name}\n"
        msg += f"  Status: {status_emoji} `{e.status}`\n"

    await send_telegram_message(chat_id, msg, parse_mode="Markdown")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if not context.args:
        await send_telegram_message(chat_id, "Usage: /cancel <execution_id>")
        return

    try:
        execution_id = int(context.args[0])
    except ValueError:
        await send_telegram_message(chat_id, "Invalid execution ID. Use a number.")
        return

    execution = await _sa(lambda: Execution.objects.filter(id=execution_id).first())()
    if execution is None:
        await send_telegram_message(chat_id, f"Execution #{execution_id} not found.")
        return

    if execution.status not in [Execution.Status.PENDING, Execution.Status.RUNNING]:
        await send_telegram_message(chat_id, f"Execution #{execution_id} is already in `{execution.status}` state and cannot be cancelled.")
        return

    await _sa(lambda: Execution.objects.filter(id=execution_id).update(status=Execution.Status.FAILED, error_message="Cancelled by user via Telegram"))()

    try:
        from apps.executions.notifications import notify_execution_failed
        await notify_execution_failed(execution_id, "Cancelled by user via Telegram")
    except Exception:
        pass

    await send_telegram_message(chat_id, f"✅ Execution #{execution_id} has been successfully cancelled.")


async def workflow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if not context.args:
        await send_telegram_message(chat_id, "Usage: /workflow <workflow_id>")
        return

    try:
        workflow_id = int(context.args[0])
    except ValueError:
        await send_telegram_message(chat_id, "Invalid workflow ID. Use a number.")
        return

    workflow = await _sa(lambda: Workflow.objects.filter(id=workflow_id, is_active=True).first())()
    if workflow is None:
        await send_telegram_message(chat_id, f"Workflow {workflow_id} not found or inactive.")
        return

    text = " ".join(context.args[1:]) or "Process via Telegram"

    execution =     await _sa(lambda: Execution.objects.create(
        workflow=workflow,
        status=Execution.Status.PENDING,
        input_data={
            "text": text,
            "telegram_chat_id": chat_id,
        },
    ))()

    execute_workflow.delay(execution.id)

    await send_telegram_message(chat_id, f"Workflow *{workflow.name}* triggered (execution #{execution.id}).", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()

    if not user_text:
        return

    await _register_user(update)

    agent = await _get_telegram_agent()
    if agent is None:
        await send_telegram_message(
            chat_id,
            "No Telegram-enabled agent found. Create an agent with `enabled_channels` containing `\"telegram\"`.",
        )
        return

    await send_telegram_message(chat_id, "Thinking...")

    try:
        provider = ProviderRegistry.instantiate(agent.provider)
        if provider is None:
            await send_telegram_message(chat_id, f"Provider `{agent.provider}` is not configured.")
            return

        recent_messages = await _get_recent_messages(chat_id, agent.id)
        llm_messages = _build_llm_messages(agent, recent_messages, user_text)

        llm_config = LLMConfig(
            model=agent.model or provider.default_model,
            temperature=agent.temperature,
        )

        response = await provider.generate(llm_messages, llm_config)

        await _persist_messages(chat_id, agent, user_text, response)

        await send_telegram_message(chat_id, response.content)

    except Exception as e:
        logger.exception("Telegram agent chat failed for %s", chat_id)
        await send_telegram_message(chat_id, f"Sorry, something went wrong: {e}")


async def _register_user(update: Update) -> None:
    chat = update.effective_chat
    await _sa(lambda: TelegramUser.objects.update_or_create(
        chat_id=chat.id,
        defaults={
            "username": chat.username or "",
            "first_name": chat.first_name or "",
            "last_name": chat.last_name or "",
        },
    ))()


async def _get_telegram_agent() -> Agent | None:
    return await _sa(
        lambda: Agent.objects.filter(
            enabled_channels__contains=["telegram"],
            is_active=True,
        ).first()
    )()


async def _get_recent_messages(chat_id: int, agent_id: int, limit: int = 20):
    return await _sa(
        lambda: list(
            HistoryMessage.objects.filter(
                channel="telegram",
                metadata__chat_id=chat_id,
                source_agent_id=agent_id,
            ).order_by("-created_at")[:limit]
        )
    )()


def _build_llm_messages(agent: Agent, recent_messages: list, user_text: str) -> list[LLMMessage]:
    messages = []
    if agent.system_prompt:
        messages.append(LLMMessage(role="system", content=agent.system_prompt))

    for msg in reversed(recent_messages):
        messages.append(LLMMessage(role=msg.role, content=msg.content))

    messages.append(LLMMessage(role="user", content=user_text))
    return messages


async def _persist_messages(chat_id: int, agent: Agent, user_text: str, response) -> None:
    common = {
        "channel": "telegram",
        "metadata": {"chat_id": chat_id},
    }

    await _sa(lambda: HistoryMessage.objects.create(
        role=HistoryMessage.Role.USER,
        content=user_text,
        source_agent=agent,
        **common,
    ))()

    await _sa(lambda: HistoryMessage.objects.create(
        role=HistoryMessage.Role.ASSISTANT,
        content=response.content,
        source_agent=agent,
        token_count=response.usage.total_tokens if response.usage else 0,
        channel="telegram",
        metadata={
            "chat_id": chat_id,
            "model": response.model,
            "finish_reason": response.finish_reason,
        },
    ))()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    caption = (update.message.caption or "").strip()

    if not caption.startswith("/workflow"):
        await send_telegram_message(
            chat_id,
            "📸 *Photo Received!*\n\nTo trigger a vision workflow using this image, please send the photo with a caption like:\n`/workflow <workflow_id> [your prompt]`",
            parse_mode="Markdown"
        )
        return

    parts = caption.split(maxsplit=2)
    if len(parts) < 2:
        await send_telegram_message(
            chat_id,
            "Invalid format. Please use caption: `/workflow <workflow_id> [prompt]`",
            parse_mode="Markdown"
        )
        return

    try:
        workflow_id = int(parts[1])
    except ValueError:
        await send_telegram_message(chat_id, "Invalid workflow ID. Use a number.")
        return

    workflow = await _sa(lambda: Workflow.objects.filter(id=workflow_id, is_active=True).first())()
    if workflow is None:
        await send_telegram_message(chat_id, f"Workflow {workflow_id} not found or inactive.")
        return

    prompt = parts[2] if len(parts) > 2 else "Analyze this image and describe it, extracting all readable text."

    await send_telegram_message(chat_id, "📥 *Downloading and processing image...*", parse_mode="Markdown")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        import base64
        encoded = base64.b64encode(photo_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{encoded}"

        await _register_user(update)

        execution = await _sa(lambda: Execution.objects.create(
            workflow=workflow,
            status=Execution.Status.PENDING,
            input_data={
                "text": prompt,
                "image_url": image_url,
                "telegram_chat_id": chat_id,
            },
        ))()

        execute_workflow.delay(execution.id)

        await send_telegram_message(
            chat_id,
            f"🚀 *Workflow '{workflow.name}' triggered successfully!*\n\n"
            f"*Execution ID:* `{execution.id}`\n"
            f"The image will be processed inline via Groq Llama 3.2 Vision. You will receive the structured output here when complete.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.exception("Failed to process Telegram photo workflow trigger")
        await send_telegram_message(chat_id, f"❌ Failed to process image workflow: {e}")

