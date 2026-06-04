from django.contrib import admin

from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["chat_id", "username", "first_name", "last_name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["username", "first_name", "last_name"]
