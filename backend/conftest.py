import os
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def token(user):
    token, _ = Token.objects.get_or_create(user=user)
    return token


@pytest.fixture
def auth_client(user, token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def agent_payload():
    return {
        "name": "ResearchAgent",
        "role": "Research specialist",
        "system_prompt": "You are a research specialist.",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_iterations": 10,
        "memory_enabled": True,
    }


@pytest.fixture
def workflow_payload():
    return {
        "name": "ResearchWorkflow",
        "description": "Research then summarize",
        "nodes": [
            {"id": "research", "type": "agent"},
            {"id": "summarize", "type": "agent"},
        ],
        "edges": [
            {"source": "research", "target": "summarize"},
        ],
    }
