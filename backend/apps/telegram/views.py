from rest_framework.viewsets import ModelViewSet

from .models import TelegramUser
from .serializers import TelegramUserSerializer


class TelegramUserViewSet(ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    search_fields = ["username", "first_name", "last_name"]
    filterset_fields = ["is_active"]

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TelegramSettings
from .serializers import TelegramSettingsSerializer

class TelegramSettingsView(APIView):
    def get(self, request):
        settings = TelegramSettings.load()
        serializer = TelegramSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings = TelegramSettings.load()
        serializer = TelegramSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
