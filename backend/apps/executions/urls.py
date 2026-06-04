from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ExecutionViewSet, sse_stream

router = DefaultRouter()
router.register("", ExecutionViewSet, basename="execution")

urlpatterns = [
    path("", include(router.urls)),
    path("<int:execution_id>/stream/", sse_stream, name="execution-sse"),
]
