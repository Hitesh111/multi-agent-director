from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "role", "channel", "source_agent", "target_agent", "created_at"]
    list_filter = ["role", "channel"]
    search_fields = ["content"]
