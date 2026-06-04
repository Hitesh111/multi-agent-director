from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agents.models import Agent
from apps.workflows.models import Workflow


@pytest.mark.django_db
class TestAgentCRUD:
    def test_create_agent(self, auth_client, agent_payload):
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201
        assert resp.json()["name"] == "ResearchAgent"
        assert resp.json()["provider"] == "deepseek"

    def test_create_agent_invalid_provider(self, auth_client, agent_payload):
        agent_payload["provider"] = "invalid"
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 400

    def test_create_agent_invalid_temperature(self, auth_client, agent_payload):
        agent_payload["temperature"] = 99
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 400

    def test_list_agents(self, auth_client, agent_payload):
        auth_client.post(reverse("agent-list"), agent_payload, format="json")
        resp = auth_client.get(reverse("agent-list"))
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_filter_by_provider(self, auth_client, agent_payload):
        auth_client.post(reverse("agent-list"), agent_payload, format="json")
        resp = auth_client.get(reverse("agent-list"), {"provider": "deepseek"})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_get_agent(self, auth_client, agent_payload):
        create_resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        agent_id = create_resp.json()["id"]
        resp = auth_client.get(reverse("agent-detail", args=[agent_id]))
        assert resp.status_code == 200
        assert resp.json()["name"] == "ResearchAgent"

    def test_update_agent(self, auth_client, agent_payload):
        create_resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        agent_id = create_resp.json()["id"]
        resp = auth_client.patch(
            reverse("agent-detail", args=[agent_id]),
            {"name": "UpdatedAgent"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "UpdatedAgent"

    def test_delete_agent(self, auth_client, agent_payload):
        create_resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        agent_id = create_resp.json()["id"]
        resp = auth_client.delete(reverse("agent-detail", args=[agent_id]))
        assert resp.status_code == 204
        assert Agent.objects.count() == 0

    def test_skills_field(self, auth_client, agent_payload):
        agent_payload["skills"] = ["python", "nlp"]
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201
        assert resp.json()["skills"] == ["python", "nlp"]

    def test_search_agents(self, auth_client, agent_payload):
        auth_client.post(reverse("agent-list"), agent_payload, format="json")
        resp = auth_client.get(reverse("agent-list"), {"search": "Research"})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_create_agent_with_schedule_config(self, auth_client, agent_payload):
        agent_payload["schedule_config"] = {"interval_minutes": 30}
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["schedule_config"] == {"interval_minutes": 30}

    def test_create_agent_with_interaction_rules(self, auth_client, agent_payload):
        agent_payload["interaction_rules"] = {"max_turns": 5, "allowed_topics": ["tech"]}
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["interaction_rules"] == {"max_turns": 5, "allowed_topics": ["tech"]}

    def test_create_agent_with_allowed_agents(self, auth_client, agent_payload):
        agent_payload["allowed_agents"] = [1, 2, 3]
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["allowed_agents"] == [1, 2, 3]

    def test_update_schedule_config(self, auth_client, agent_payload):
        create_resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        agent_id = create_resp.json()["id"]
        resp = auth_client.patch(
            reverse("agent-detail", args=[agent_id]),
            {"schedule_config": {"cron": "0 */12 * * *"}},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["schedule_config"] == {"cron": "0 */12 * * *"}

    def test_unauthenticated_returns_403(self, api_client):
        resp = api_client.get(reverse("agent-list"))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAgentScheduler:
    def test_interval_matches_and_triggers_workflow(self, auth_client, agent_payload, workflow_payload):
        agent_payload["schedule_config"] = {"interval_minutes": 30}
        agent_resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        agent_id = agent_resp.json()["id"]
        workflow_payload["nodes"] = [
            {"id": "node1", "type": "agent", "agentId": agent_id},
        ]
        wf_resp = auth_client.post(reverse("workflow-list"), workflow_payload, format="json")
        assert wf_resp.status_code == 201

        from apps.agents.tasks import check_agent_schedules
        agent = Agent.objects.get(id=agent_id)
        cfg = dict(agent.schedule_config)
        cfg.pop("last_fired_at", None)
        agent.schedule_config = cfg
        agent.save()

        with patch("runtime.executor.execute_workflow.delay") as mock_delay:
            result = check_agent_schedules()
            assert result == 1
            mock_delay.assert_called_once()

        agent.refresh_from_db()
        assert "last_fired_at" in agent.schedule_config

    def test_interval_skips_if_recently_fired(self, auth_client, agent_payload):
        agent_payload["schedule_config"] = {"interval_minutes": 30, "last_fired_at": timezone.now().isoformat()}
        resp = auth_client.post(reverse("agent-list"), agent_payload, format="json")
        assert resp.status_code == 201

        from apps.agents.tasks import check_agent_schedules
        result = check_agent_schedules()
        assert result == 0

    def test_inactive_agent_not_scheduled(self, auth_client, agent_payload):
        agent_payload["schedule_config"] = {"interval_minutes": 30}
        agent_payload["is_active"] = False
        auth_client.post(reverse("agent-list"), agent_payload, format="json")

        from apps.agents.tasks import check_agent_schedules
        result = check_agent_schedules()
        assert result == 0

    def test_no_schedule_config_skipped(self, auth_client, agent_payload):
        auth_client.post(reverse("agent-list"), agent_payload, format="json")

        from apps.agents.tasks import check_agent_schedules
        result = check_agent_schedules()
        assert result == 0
