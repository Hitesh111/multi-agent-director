import pytest
from django.urls import reverse

from apps.agents.models import Agent
from apps.workflows.models import Workflow
from apps.executions.models import Execution


@pytest.mark.django_db
class TestWorkflowCRUD:
    def test_create_workflow(self, auth_client, workflow_payload):
        resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        assert resp.status_code == 201
        assert resp.json()["name"] == "ResearchWorkflow"

    def test_create_workflow_invalid_nodes(self, auth_client, workflow_payload):
        workflow_payload["nodes"] = "not-a-list"
        resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        assert resp.status_code == 400

    def test_create_workflow_missing_edge_fields(self, auth_client, workflow_payload):
        workflow_payload["edges"] = [{"bad": "data"}]
        resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        assert resp.status_code == 400

    def test_list_workflows(self, auth_client, workflow_payload):
        auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        resp = auth_client.get(reverse("workflow-list"))
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_update_workflow(self, auth_client, workflow_payload):
        create_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = create_resp.json()["id"]
        resp = auth_client.patch(
            reverse("workflow-detail", args=[wf_id]),
            {"description": "Updated description"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    def test_delete_workflow(self, auth_client, workflow_payload):
        create_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = create_resp.json()["id"]
        resp = auth_client.delete(reverse("workflow-detail", args=[wf_id]))
        assert resp.status_code == 204
        assert Workflow.objects.count() == 0

    def test_trigger_execution(self, auth_client, workflow_payload):
        create_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = create_resp.json()["id"]
        resp = auth_client.post(
            reverse("workflow-trigger", args=[wf_id]),
            {"input_data": {"topic": "AI agents"}},
            format="json",
        )
        assert resp.status_code == 201
        execution = resp.json()
        assert execution["status"] == "running"
        assert execution["workflow"] == wf_id
        assert len(execution["node_states"]) == 2

    def test_trigger_inactive_workflow(self, auth_client, workflow_payload):
        create_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = create_resp.json()["id"]
        Workflow.objects.filter(id=wf_id).update(is_active=False)
        resp = auth_client.post(
            reverse("workflow-trigger", args=[wf_id]),
            {"input_data": {}},
            format="json",
        )
        assert resp.status_code == 400

    def test_trigger_with_agent_assignment(self, auth_client, workflow_payload):
        agent = Agent.objects.create(name="TestAgent", provider="deepseek")
        workflow_payload["nodes"] = [
            {"id": "n1", "type": "agent", "agentId": agent.id},
        ]
        workflow_payload["edges"] = []
        create_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = create_resp.json()["id"]
        resp = auth_client.post(
            reverse("workflow-trigger", args=[wf_id]),
            {"input_data": {}},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["node_states"][0]["agent"] == agent.id
