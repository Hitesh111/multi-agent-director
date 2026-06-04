import pytest
from unittest.mock import patch, AsyncMock

from apps.agents.models import Agent
from apps.workflows.models import Workflow
from apps.executions.models import Execution, ExecutionNode
from runtime.executor import execute_workflow


@pytest.mark.django_db(transaction=True)
class TestCeleryExecutor:
    @patch("runtime.executor.WorkflowEngine.run")
    def test_execute_workflow_task(self, mock_engine_run):
        mock_engine_run.return_value = None

        agent = Agent.objects.create(name="ExecTestAgent1", provider="deepseek")
        wf = Workflow.objects.create(
            name="ExecTestWF1",
            nodes=[{"id": "n1", "type": "agent", "agentId": agent.id}],
            edges=[],
        )
        execution = Execution.objects.create(
            workflow=wf,
            status=Execution.Status.RUNNING,
            input_data={},
        )

        execute_workflow(execution.id)
        mock_engine_run.assert_called_once_with(execution.id)
