from django.contrib import admin

from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["name", "provider", "model", "is_active", "created_at"]
    list_filter = ["provider", "is_active", "memory_enabled"]
    search_fields = ["name", "role"]
