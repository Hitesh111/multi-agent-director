from rest_framework import serializers

from .models import TelegramUser


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "chat_id",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class TelegramSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__('apps.telegram.models', fromlist=['TelegramSettings']).TelegramSettings
        fields = ["bot_token", "updated_at"]
        read_only_fields = ["updated_at"]
