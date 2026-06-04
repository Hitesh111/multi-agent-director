import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from asgiref.sync import sync_to_async

from apps.agents.models import Agent
from apps.history.models import Message as HistoryMessage
from apps.telegram.models import TelegramUser
from apps.workflows.models import Workflow
from apps.executions.models import Execution, ExecutionNode
from apps.telegram.handlers import (
    _get_telegram_agent,
    _build_llm_messages,
    handle_message,
    start_command,
    help_command,
    workflow_command,
    _register_user,
    _persist_messages,
    workflows_command,
    agents_command,
    executions_command,
    cancel_command,
)
from apps.telegram.actions import send_telegram_message, send_telegram_message_sync
from runtime.executor import _send_telegram_response
from llm.schemas import LLMResponse, TokenUsage


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def telegram_agent():
    return Agent.objects.create(
        name="TelegramAgent",
        system_prompt="You are a Telegram agent.",
        provider="deepseek",
        enabled_channels=["telegram"],
        is_active=True,
    )


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_chat.username = "testuser"
    update.effective_chat.first_name = "Test"
    update.effective_chat.last_name = "User"
    update.message.text = "Hello"
    update.message.chat.id = 12345
    return update


@pytest.fixture
def mock_context():
    return MagicMock()


class TestTelegramAgentLookup:
    async def test_returns_first_telegram_enabled_agent(self, telegram_agent):
        agent = await _get_telegram_agent()
        assert agent is not None
        assert agent.id == telegram_agent.id

    async def test_returns_none_if_no_agent(self):
        agent = await _get_telegram_agent()
        assert agent is None

    async def test_ignores_inactive_agents(self, telegram_agent):
        telegram_agent.is_active = False
        await sync_to_async(telegram_agent.save)()
        agent = await _get_telegram_agent()
        assert agent is None


class TestBuildLLMMessages:
    def test_includes_system_prompt(self, telegram_agent):
        recent = []
        messages = _build_llm_messages(telegram_agent, recent, "hi")
        assert len(messages) >= 1
        assert messages[0].role == "system"
        assert messages[0].content == "You are a Telegram agent."

    def test_appends_user_message(self, telegram_agent):
        messages = _build_llm_messages(telegram_agent, [], "hello")
        assert messages[-1].role == "user"
        assert messages[-1].content == "hello"

    def test_includes_history_in_order(self, telegram_agent):
        msg1 = MagicMock(role="user", content="first")
        msg2 = MagicMock(role="assistant", content="second")
        messages = _build_llm_messages(telegram_agent, [msg1, msg2], "third")
        contents = [m.content for m in messages]
        assert "first" in contents
        assert "second" in contents
        assert messages[-1].content == "third"


class TestPersistMessages:
    async def test_creates_user_and_assistant_messages(self, telegram_agent):
        resp = LLMResponse(
            content="Response text",
            model="deepseek-chat",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=20, completion_tokens=22, total_tokens=42),
        )

        await _persist_messages(12345, telegram_agent, "User text", resp)

        msgs = await sync_to_async(
            lambda: list(HistoryMessage.objects.filter(channel="telegram"))
        )()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "User text"
        assert msgs[1].role == "assistant"
        assert msgs[1].content == "Response text"
        assert msgs[1].token_count == 42


class TestRegisterUser:
    async def test_creates_new_user(self, mock_update):
        await _register_user(mock_update)
        user = await sync_to_async(TelegramUser.objects.get)(chat_id=12345)
        assert user.username == "testuser"

    async def test_updates_existing_user(self, mock_update):
        await sync_to_async(TelegramUser.objects.create)(
            chat_id=12345, username="old", first_name="Old"
        )
        await _register_user(mock_update)
        user = await sync_to_async(TelegramUser.objects.get)(chat_id=12345)
        assert user.first_name == "Test"


class TestHandleMessage:
    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    @patch("apps.telegram.handlers.ProviderRegistry.instantiate")
    async def test_responds_via_agent(
        self, mock_provider, mock_send, telegram_agent, mock_update, mock_context
    ):
        mock_instance = AsyncMock()
        mock_instance.generate.return_value = LLMResponse(
            content="Hello back!",
            model="deepseek-chat",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
        mock_instance.default_model = "deepseek-chat"
        mock_provider.return_value = mock_instance

        await handle_message(mock_update, mock_context)

        assert mock_instance.generate.called
        assert mock_send.called
        last_call = mock_send.call_args_list[-1]
        assert last_call[0][1] == "Hello back!"

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_no_agent_message(self, mock_send, mock_update, mock_context):
        await handle_message(mock_update, mock_context)

        assert mock_send.called
        last_call = mock_send.call_args_list[-1]
        assert "No Telegram-enabled agent" in last_call[0][1]


class TestCommands:
    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_start_command(self, mock_send, mock_update, mock_context):
        await start_command(mock_update, mock_context)
        assert mock_send.called
        assert "Welcome" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_help_command(self, mock_send, mock_update, mock_context):
        await help_command(mock_update, mock_context)
        assert mock_send.called
        assert "Available commands" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    @patch("apps.telegram.handlers.execute_workflow")
    async def test_workflow_command_triggers_execution(
        self, mock_execute, mock_send, mock_update, mock_context
    ):
        agent = Agent.objects.create(name="WfAgent", provider="deepseek")
        wf = Workflow.objects.create(
            name="TestWF",
            nodes=[{"id": "n1", "type": "agent", "agentId": agent.id}],
        )
        mock_context.args = [str(wf.id), "do the thing"]

        await workflow_command(mock_update, mock_context)

        assert mock_send.called
        assert "TestWF" in mock_send.call_args[0][1]
        assert mock_execute.delay.called


class TestSendTelegramResponse:
    # Patch send_telegram_message_sync at the executor import site so we don't
    # need to deal with the async-context-manager Bot internals in unit tests.
    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_sends_to_correct_chat(self, mock_sync_send):
        agent = Agent.objects.create(name="TgAgent", provider="deepseek")
        wf = Workflow.objects.create(
            name="TgWF",
            nodes=[{"id": "n1", "type": "agent", "agentId": agent.id}],
        )
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.COMPLETED,
            input_data={"telegram_chat_id": 999},
            output_data={"content": "Workflow done"},
        )

        _send_telegram_response(execution.id)

        mock_sync_send.assert_called_once_with(999, "Workflow done", parse_mode=None)

    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_skips_if_no_chat_id(self, mock_sync_send):
        execution = Execution.objects.create(
            workflow=Workflow.objects.create(name="NoTgWF", nodes=[{"id": "n1"}]),
            status=Execution.Status.COMPLETED,
            input_data={},
            output_data={"content": "done"},
        )
        _send_telegram_response(execution.id)
        mock_sync_send.assert_not_called()

    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_sends_node_results(self, mock_sync_send):
        wf = Workflow.objects.create(name="ComplexWF", nodes=[{"id": "research"}, {"id": "review"}])
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.COMPLETED,
            input_data={"telegram_chat_id": 999},
            output_data={"node_results": {"research": "Some research", "review": "Final output content"}},
        )
        _send_telegram_response(execution.id)
        mock_sync_send.assert_called_once()
        args, kwargs = mock_sync_send.call_args
        assert args[0] == 999
        assert "ComplexWF" in args[1]
        assert "Final output content" in args[1]

    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_sends_failure_response(self, mock_sync_send):
        wf = Workflow.objects.create(name="FailWF", nodes=[{"id": "n1"}])
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.FAILED,
            input_data={"telegram_chat_id": 999},
            error_message="API connection timeout",
        )
        _send_telegram_response(execution.id)
        mock_sync_send.assert_called_once()
        args, kwargs = mock_sync_send.call_args
        assert args[0] == 999
        assert "Execution Failed" in args[1]
        assert "FailWF" in args[1]
        assert "API connection timeout" in args[1]

    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_sends_needs_approval_response(self, mock_sync_send):
        wf = Workflow.objects.create(name="ApprovalWF", nodes=[{"id": "n1"}])
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.NEEDS_APPROVAL,
            input_data={"telegram_chat_id": 999},
        )
        _send_telegram_response(execution.id)
        mock_sync_send.assert_called_once()
        args, kwargs = mock_sync_send.call_args
        assert args[0] == 999
        assert "Awaiting Approval" in args[1]
        assert "ApprovalWF" in args[1]

    @patch("apps.telegram.actions.send_telegram_message_sync")
    def test_sends_cancelled_response(self, mock_sync_send):
        wf = Workflow.objects.create(name="CancelWF", nodes=[{"id": "n1"}])
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.CANCELLED,
            input_data={"telegram_chat_id": 999},
        )
        _send_telegram_response(execution.id)
        mock_sync_send.assert_called_once()
        args, kwargs = mock_sync_send.call_args
        assert args[0] == 999
        assert "Cancelled" in args[1]
        assert "CancelWF" in args[1]


class TestSendTelegramMessage:
    @patch("apps.telegram.actions.Bot", autospec=True)
    @patch("apps.telegram.actions.settings")
    @pytest.mark.asyncio
    async def test_sends_message(self, mock_settings, mock_bot_cls):
        mock_settings.TELEGRAM_BOT_TOKEN = "fake:token"
        mock_bot_instance = AsyncMock()
        mock_bot_cls.return_value.__aenter__ = AsyncMock(return_value=mock_bot_instance)
        mock_bot_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_telegram_message(12345, "Hello")
        assert result is True
        mock_bot_instance.send_message.assert_called_once_with(
            chat_id=12345, text="Hello", parse_mode="Markdown"
        )

    @patch("apps.telegram.actions.Bot", autospec=True)
    @patch("apps.telegram.actions.settings")
    @pytest.mark.asyncio
    async def test_handles_error(self, mock_settings, mock_bot_cls):
        from telegram.error import TelegramError
        mock_settings.TELEGRAM_BOT_TOKEN = "fake:token"
        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message.side_effect = TelegramError("API error")
        mock_bot_cls.return_value.__aenter__ = AsyncMock(return_value=mock_bot_instance)
        mock_bot_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await send_telegram_message(12345, "Hello")
        assert result is False


class TestExtendedCommands:
    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_workflows_command(self, mock_send, mock_update, mock_context):
        await sync_to_async(Workflow.objects.create)(name="Research Flow", is_active=True, nodes=[{"id": "n1"}])
        await workflows_command(mock_update, mock_context)
        assert mock_send.called
        assert "Research Flow" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_agents_command(self, mock_send, mock_update, mock_context):
        await sync_to_async(Agent.objects.create)(name="CoderAgent", provider="deepseek", is_active=True)
        await agents_command(mock_update, mock_context)
        assert mock_send.called
        assert "CoderAgent" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_executions_command(self, mock_send, mock_update, mock_context):
        wf = await sync_to_async(Workflow.objects.create)(name="ExecFlow", nodes=[{"id": "n1"}])
        await sync_to_async(Execution.objects.create)(workflow=wf, status=Execution.Status.COMPLETED)
        await executions_command(mock_update, mock_context)
        assert mock_send.called
        assert "ExecFlow" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    async def test_cancel_command_running(self, mock_send, mock_update, mock_context):
        wf = await sync_to_async(Workflow.objects.create)(name="CancelFlow", nodes=[{"id": "n1"}])
        exec_obj = await sync_to_async(Execution.objects.create)(workflow=wf, status=Execution.Status.RUNNING)
        mock_context.args = [str(exec_obj.id)]
        await cancel_command(mock_update, mock_context)
        assert mock_send.called
        assert "successfully cancelled" in mock_send.call_args[0][1]

        # Verify state in DB
        await sync_to_async(exec_obj.refresh_from_db)()
        assert exec_obj.status == Execution.Status.FAILED


class TestTelegramPhotoHandler:
    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_handle_photo_no_caption(self, mock_send, mock_update, mock_context):
        mock_update.message.caption = None
        mock_update.effective_chat.id = 999

        from apps.telegram.handlers import handle_photo
        await handle_photo(mock_update, mock_context)

        assert mock_send.called
        assert "To trigger a vision workflow" in mock_send.call_args[0][1]

    @patch("apps.telegram.handlers.execute_workflow")
    @patch("apps.telegram.handlers.send_telegram_message", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_handle_photo_success(self, mock_send, mock_execute_delay, mock_update, mock_context):
        wf = await sync_to_async(Workflow.objects.create)(name="VisionTestFlow", is_active=True, nodes=[{"id": "n1"}])
        
        mock_update.message.caption = f"/workflow {wf.id} OCR this receipt"
        mock_update.effective_chat.id = 999

        mock_photo = MagicMock()
        mock_photo.get_file = AsyncMock()
        
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=b"fake-image-bytes")
        mock_photo.get_file.return_value = mock_file
        
        mock_update.message.photo = [mock_photo]

        from apps.telegram.handlers import handle_photo
        await handle_photo(mock_update, mock_context)

        assert mock_send.call_count >= 2
        execution = await sync_to_async(Execution.objects.filter(workflow=wf).first)()
        assert execution is not None
        assert execution.status == Execution.Status.PENDING
        assert execution.input_data["text"] == "OCR this receipt"
        assert execution.input_data["telegram_chat_id"] == 999
        assert execution.input_data["image_url"].startswith("data:image/jpeg;base64,")
        
        mock_execute_delay.delay.assert_called_once_with(execution.id)
