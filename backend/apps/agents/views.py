from rest_framework.viewsets import ModelViewSet

from .models import Agent
from .serializers import AgentSerializer


class AgentViewSet(ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    search_fields = ["name", "role", "system_prompt"]
    filterset_fields = ["provider", "is_active", "memory_enabled"]
