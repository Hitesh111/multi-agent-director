import pytest
from django.urls import reverse
from django.utils import timezone

from apps.workflows.models import Workflow
from apps.executions.models import Execution, ExecutionNode


@pytest.mark.django_db
class TestExecutionCRUD:
    def test_list_executions(self, auth_client, workflow_payload):
        wf_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = wf_resp.json()["id"]
        auth_client.post(reverse("workflow-trigger", args=[wf_id]), {"input_data": {}}, format="json")
        resp = auth_client.get(reverse("execution-list"))
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_get_execution(self, auth_client, workflow_payload):
        wf_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = wf_resp.json()["id"]
        trigger_resp = auth_client.post(
            reverse("workflow-trigger", args=[wf_id]), {"input_data": {}}, format="json"
        )
        exec_id = trigger_resp.json()["id"]
        resp = auth_client.get(reverse("execution-detail", args=[exec_id]))
        assert resp.status_code == 200
        assert resp.json()["id"] == exec_id

    def test_cancel_execution(self, auth_client, workflow_payload):
        wf_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = wf_resp.json()["id"]
        trigger_resp = auth_client.post(
            reverse("workflow-trigger", args=[wf_id]), {"input_data": {}}, format="json"
        )
        exec_id = trigger_resp.json()["id"]
        resp = auth_client.post(reverse("execution-cancel", args=[exec_id]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_filter_by_status(self, auth_client, workflow_payload):
        wf_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        wf_id = wf_resp.json()["id"]
        auth_client.post(reverse("workflow-trigger", args=[wf_id]), {"input_data": {}}, format="json")
        resp = auth_client.get(reverse("execution-list"), {"status": "running"})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1
        resp = auth_client.get(reverse("execution-list"), {"status": "completed"})
        assert len(resp.json()["results"]) == 0
