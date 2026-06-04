from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "execution",
            "execution_node",
            "source_agent",
            "target_agent",
            "role",
            "content",
            "metadata",
            "token_count",
            "channel",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
