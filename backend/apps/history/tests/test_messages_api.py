import pytest
from django.urls import reverse

from apps.agents.models import Agent
from apps.workflows.models import Workflow
from apps.history.models import Message


@pytest.mark.django_db
class TestMessageAPI:
    def test_create_message(self, auth_client):
        agent = Agent.objects.create(name="TestAgent", provider="deepseek")
        wf = Workflow.objects.create(name="TestWF", nodes=[], edges=[])
        resp = auth_client.post(
            reverse("message-list"),
            {
                "role": "user",
                "content": "Hello",
                "source_agent": agent.id,
                "channel": "telegram",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hello"

    def test_list_messages(self, auth_client):
        agent = Agent.objects.create(name="TestAgent", provider="deepseek")
        Message.objects.create(role="user", content="Msg1", source_agent=agent)
        Message.objects.create(role="assistant", content="Msg2", source_agent=agent)
        resp = auth_client.get(reverse("message-list"))
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2

    def test_filter_by_role(self, auth_client):
        agent = Agent.objects.create(name="TestAgent", provider="deepseek")
        Message.objects.create(role="user", content="User msg", source_agent=agent)
        Message.objects.create(role="assistant", content="Bot reply", source_agent=agent)
        resp = auth_client.get(reverse("message-list"), {"role": "user"})
        assert len(resp.json()["results"]) == 1

    def test_delete_message(self, auth_client):
        agent = Agent.objects.create(name="TestAgent", provider="deepseek")
        msg = Message.objects.create(role="user", content="Delete me", source_agent=agent)
        resp = auth_client.delete(reverse("message-detail", args=[msg.id]))
        assert resp.status_code == 204
