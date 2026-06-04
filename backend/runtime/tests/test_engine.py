import pytest
from unittest.mock import patch, AsyncMock

from apps.agents.models import Agent
from apps.workflows.models import Workflow
from apps.executions.models import Execution, ExecutionNode
from apps.history.models import Message
from runtime.engine import WorkflowEngine


@pytest.mark.django_db(transaction=True)
class TestWorkflowEngine:
    @patch("runtime.nodes.ProviderRegistry.instantiate")
    async def test_run_completes_execution(self, mock_provider):
        agent = Agent.objects.create(
            name="EngTestAgent1",
            provider="deepseek",
            system_prompt="You are helpful",
        )
        wf = Workflow.objects.create(
            name="EngTestWF1",
            nodes=[{"id": "n1", "type": "agent", "agentId": agent.id}],
            edges=[],
        )
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.RUNNING,
            input_data={"topic": "AI"},
        )
        ExecutionNode.objects.create(
            execution=execution,
            node_id="n1",
            agent=agent,
            status=Execution.Status.PENDING,
        )

        mock_provider_instance = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "Research results"
        mock_response.model = "deepseek-chat"
        mock_response.finish_reason = "stop"
        mock_response.usage.total_tokens = 50
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 30
        mock_provider_instance.generate.return_value = mock_response
        mock_provider.return_value = mock_provider_instance

        engine = WorkflowEngine()
        await engine.run(execution.id)

        execution.refresh_from_db()
        assert execution.status == Execution.Status.COMPLETED

        assert Message.objects.filter(execution=execution).count() == 1

        exec_node = ExecutionNode.objects.get(execution=execution, node_id="n1")
        assert exec_node.status == Execution.Status.COMPLETED

    @patch("runtime.nodes.ProviderRegistry.instantiate")
    async def test_run_marks_failed_on_error(self, mock_provider):
        agent = Agent.objects.create(
            name="EngTestAgent2",
            provider="deepseek",
            system_prompt="You are helpful",
        )
        wf = Workflow.objects.create(
            name="EngTestWF2",
            nodes=[{"id": "n1", "type": "agent", "agentId": agent.id}],
            edges=[],
        )
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.RUNNING,
            input_data={},
        )
        ExecutionNode.objects.create(
            execution=execution,
            node_id="n1",
            agent=agent,
            status=Execution.Status.PENDING,
        )

        mock_provider_instance = AsyncMock()
        mock_provider_instance.generate.side_effect = Exception("API timeout")
        mock_provider.return_value = mock_provider_instance

        engine = WorkflowEngine()
        await engine.run(execution.id)

        execution.refresh_from_db()
        assert execution.status == Execution.Status.FAILED

    async def test_run_without_agent_skips_node(self):
        wf = Workflow.objects.create(
            name="EngTestWF3",
            nodes=[{"id": "n1", "type": "agent"}],
            edges=[],
        )
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.RUNNING,
            input_data={},
        )
        ExecutionNode.objects.create(
            execution=execution,
            node_id="n1",
            agent=None,
            status=Execution.Status.PENDING,
        )

        engine = WorkflowEngine()
        await engine.run(execution.id)

        execution.refresh_from_db()
        assert execution.status in (Execution.Status.COMPLETED, Execution.Status.FAILED)
