from django.contrib import admin
from django.urls import path, include

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.agents.models import Agent
from apps.workflows.models import Workflow
from apps.executions.models import Execution
from config import auth_views


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    execs = Execution.objects.all()
    status_counts = {}
    for s, _ in Execution.Status.choices:
        status_counts[s] = execs.filter(status=s).count()
    return Response({
        "agents": Agent.objects.count(),
        "workflows": Workflow.objects.count(),
        "executions": execs.count(),
        "execution_statuses": status_counts,
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", auth_views.login, name="api-login"),
    path("api/auth/register/", auth_views.register, name="api-register"),
    path("api/auth/logout/", auth_views.logout, name="api-logout"),
    path("api/stats/", dashboard_stats, name="dashboard-stats"),
    path("api/agents/", include("apps.agents.urls")),
    path("api/workflows/", include("apps.workflows.urls")),
    path("api/executions/", include("apps.executions.urls")),
    path("api/messages/", include("apps.history.urls")),
    path("api/telegram/", include("apps.telegram.urls")),
]
