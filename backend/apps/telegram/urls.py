from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TelegramUserViewSet, TelegramSettingsView

router = DefaultRouter()
router.register("users", TelegramUserViewSet, basename="telegram-user")

urlpatterns = [
    path("settings/", TelegramSettingsView.as_view(), name="telegram-settings"),
    path("", include(router.urls)),
]
