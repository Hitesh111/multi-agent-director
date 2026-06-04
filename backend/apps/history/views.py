from rest_framework.viewsets import ModelViewSet

from .models import Message
from .serializers import MessageSerializer


class MessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = [
        "execution",
        "execution_node",
        "source_agent",
        "target_agent",
        "role",
        "channel",
    ]
    ordering = ["created_at"]
