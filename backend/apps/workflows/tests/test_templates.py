import pytest
from io import StringIO
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from apps.agents.models import Agent
from apps.workflows.models import Workflow


pytestmark = pytest.mark.django_db


class TestSeedDemoCommand:
    def test_creates_seven_agents(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        assert Agent.objects.count() == 7
        assert Agent.objects.filter(name="ResearchAgent").exists()
        assert Agent.objects.filter(name="SummarizerAgent").exists()
        assert Agent.objects.filter(name="ReviewerAgent").exists()
        assert Agent.objects.filter(name="CodeWriterAgent").exists()
        assert Agent.objects.filter(name="CodeReviewerAgent").exists()
        assert Agent.objects.filter(name="ImageAnalyzerAgent").exists()
        assert Agent.objects.filter(name="DraftWriterAgent").exists()

    def test_creates_workflow_with_three_nodes(self):
        call_command("seed_demo")
        wf = Workflow.objects.filter(name="Research → Summarize → Review").first()
        assert wf is not None
        assert len(wf.nodes) == 3
        assert len(wf.edges) == 2
        assert wf.is_active is True

    def test_creates_image_analyzer_workflow(self):
        call_command("seed_demo")
        wf = Workflow.objects.filter(name="Image Analyzer").first()
        assert wf is not None
        assert len(wf.nodes) == 1
        assert len(wf.edges) == 0
        assert wf.is_active is True

    def test_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")
        assert Agent.objects.count() == 7
        assert Workflow.objects.count() == 4

    def test_agents_have_correct_prompts(self):
        call_command("seed_demo")
        research = Agent.objects.get(name="ResearchAgent")
        assert "research specialist" in research.system_prompt.lower()
        summarizer = Agent.objects.get(name="SummarizerAgent")
        assert "summarization" in summarizer.system_prompt.lower()
        reviewer = Agent.objects.get(name="ReviewerAgent")
        assert "quality" in reviewer.system_prompt.lower()

    def test_workflow_node_ids(self):
        call_command("seed_demo")
        wf = Workflow.objects.get(name="Research → Summarize → Review")
        node_ids = [n["id"] for n in wf.nodes]
        assert node_ids == ["research", "summarize", "review"]

    def test_draft_approve_workflow_has_human_approval_node(self):
        call_command("seed_demo")
        wf = Workflow.objects.get(name="Draft & Approve")
        assert len(wf.nodes) == 4
        node_types = [n["type"] for n in wf.nodes]
        assert "human_approval" in node_types
        assert "input" in node_types
        assert "output" in node_types
        assert len(wf.edges) == 3


class TestDeployTemplateEndpoint:
    @pytest.fixture
    def auth_client(self):
        user = User.objects.create_user(username="template_tester", password="pass")
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def test_returns_workflow_id(self, auth_client):
        response = auth_client.post("/api/workflows/deploy_template/")
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] is not None
        assert "message" in data

    def test_creates_agents_and_workflow(self, auth_client):
        auth_client.post("/api/workflows/deploy_template/")
        assert Agent.objects.count() == 7
        assert Workflow.objects.count() == 4

    def test_idempotent_endpoint(self, auth_client):
        auth_client.post("/api/workflows/deploy_template/")
        auth_client.post("/api/workflows/deploy_template/")
        assert Agent.objects.count() == 7
        assert Workflow.objects.count() == 4
