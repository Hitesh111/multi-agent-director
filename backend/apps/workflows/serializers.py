from rest_framework import serializers

from .models import Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "description",
            "nodes",
            "edges",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_nodes(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("nodes must be a list")
        seen_ids = set()
        for node in value:
            if not isinstance(node, dict):
                raise serializers.ValidationError("Each node must be an object")
            node_id = node.get("id")
            if not node_id:
                raise serializers.ValidationError("Each node must have an 'id' field")
            if node_id in seen_ids:
                raise serializers.ValidationError(f"Duplicate node id: {node_id}")
            seen_ids.add(node_id)
        return value

    def validate_edges(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("edges must be a list")
        for edge in value:
            if not isinstance(edge, dict):
                raise serializers.ValidationError("Each edge must be an object")
            if "source" not in edge or "target" not in edge:
                raise serializers.ValidationError(
                    "Each edge must have 'source' and 'target' fields"
                )
        return value
