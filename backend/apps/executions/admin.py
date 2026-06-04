from django.contrib import admin

from .models import Execution, ExecutionNode


class ExecutionNodeInline(admin.TabularInline):
    model = ExecutionNode
    extra = 0


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ["id", "workflow", "status", "started_at", "completed_at"]
    list_filter = ["status"]
    inlines = [ExecutionNodeInline]
