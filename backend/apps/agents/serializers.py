from rest_framework import serializers

from .models import Agent


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "role",
            "system_prompt",
            "provider",
            "model",
            "tools",
            "skills",
            "memory_enabled",
            "temperature",
            "max_iterations",
            "schedule_config",
            "interaction_rules",
            "allowed_agents",
            "enabled_channels",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_temperature(self, value):
        if value < 0.0 or value > 2.0:
            raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value

    def validate_max_iterations(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("max_iterations must be between 1 and 100")
        return value

    def validate_allowed_agents(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("allowed_agents must be a list")
        return value
