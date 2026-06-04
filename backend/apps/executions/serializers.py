from rest_framework import serializers

from .models import Execution, ExecutionNode


class ExecutionNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionNode
        fields = [
            "id",
            "execution",
            "node_id",
            "agent",
            "status",
            "input_data",
            "output_data",
            "error_message",
            "retry_count",
            "started_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "started_at", "completed_at"]


class ExecutionSerializer(serializers.ModelSerializer):
    node_states = ExecutionNodeSerializer(many=True, read_only=True)

    class Meta:
        model = Execution
        fields = [
            "id",
            "workflow",
            "status",
            "input_data",
            "output_data",
            "error_message",
            "token_usage",
            "node_states",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "started_at", "completed_at", "created_at", "updated_at"]


class CreateExecutionSerializer(serializers.Serializer):
    input_data = serializers.JSONField(default=dict)

    def validate_input_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("input_data must be a JSON object")
        return value
