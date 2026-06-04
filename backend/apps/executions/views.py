import json
import time
import logging

from django.utils import timezone
from django.http import StreamingHttpResponse

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import Execution, ExecutionNode, ExecutionEvent
from .serializers import ExecutionSerializer, CreateExecutionSerializer
from .notifications import notify_execution_approved

logger = logging.getLogger(__name__)


def sse_stream(request, execution_id):
    """SSE endpoint: clients connect via EventSource to receive live execution events.

    Uses database polling — new ExecutionEvent rows are consumed in near real-time
    and pushed to the client. Supports Last-Event-ID for reconnection resilience.
    Closes when the execution reaches a terminal state.
    """
    last_id = int(request.META.get("HTTP_LAST_EVENT_ID", 0))
    keepalive_interval = 15  # seconds between keepalive comments
    last_keepalive = time.monotonic()

    def event_stream():
        nonlocal last_id, last_keepalive

        while True:
            events = list(
                ExecutionEvent.objects
                .filter(execution_id=execution_id, id__gt=last_id)
                .order_by("id")
                .values("id", "event_type", "data")
            )

            for ev in events:
                payload = json.dumps({"type": ev["event_type"], "data": ev["data"]})
                yield f"id: {ev['id']}\ndata: {payload}\n\n"
                last_id = ev["id"]

                if ev["event_type"] in ("execution.completed", "execution.failed", "execution.cancelled"):
                    return

            # Check if execution terminated without a final event
            if not events:
                try:
                    exec_status = Execution.objects.values_list("status", flat=True).get(id=execution_id)
                    if exec_status in ("completed", "failed", "cancelled"):
                        return
                except Execution.DoesNotExist:
                    return

            now = time.monotonic()
            if now - last_keepalive >= keepalive_interval:
                yield ": keepalive\n\n"
                last_keepalive = now

            time.sleep(0.5)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


class ExecutionViewSet(ModelViewSet):
    queryset = Execution.objects.all()
    serializer_class = ExecutionSerializer
    filterset_fields = ["workflow", "status"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        execution = self.get_object()
        if execution.status in ("pending", "running"):
            execution.status = Execution.Status.CANCELLED
            execution.completed_at = timezone.now()
            execution.save(update_fields=["status", "completed_at"])

            execution.node_states.filter(
                status__in=("pending", "running")
            ).update(
                status=Execution.Status.CANCELLED,
                completed_at=timezone.now(),
            )
            ExecutionEvent.objects.create(
                execution_id=execution.id,
                event_type="execution.cancelled",
                data={"execution_id": execution.id, "error": ""},
            )
        return Response(ExecutionSerializer(execution).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        execution = self.get_object()
        approved = request.data.get("approved", True)
        feedback = request.data.get("feedback", "")

        if execution.status != Execution.Status.NEEDS_APPROVAL:
            return Response(
                {"error": f"Execution is {execution.status}, not awaiting approval"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not approved:
            execution.status = Execution.Status.CANCELLED
            execution.completed_at = timezone.now()
            output = dict(execution.output_data or {})
            output["rejected"] = True
            output["feedback"] = feedback
            execution.output_data = output
            execution.save(update_fields=["status", "completed_at", "output_data"])

            execution.node_states.filter(status__in=("pending", "needs_approval")).update(
                status=Execution.Status.CANCELLED,
                completed_at=timezone.now(),
            )
            ExecutionEvent.objects.create(
                execution_id=execution.id,
                event_type="execution.cancelled",
                data={"execution_id": execution.id, "reason": "rejected", "feedback": feedback},
            )
            return Response(ExecutionSerializer(execution).data)

        approval_node = execution.node_states.filter(status="needs_approval").first()
        if not approval_node:
            return Response(
                {"error": "No node awaiting approval found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approval_node.status = Execution.Status.COMPLETED
        approval_node.completed_at = timezone.now()
        approval_node.output_data = {"approved": True, "feedback": feedback}
        approval_node.save(update_fields=["status", "completed_at", "output_data"])

        execution.status = Execution.Status.RUNNING
        execution.save(update_fields=["status"])

        ExecutionEvent.objects.create(
            execution_id=execution.id,
            event_type="execution.approved",
            data={"execution_id": execution.id, "approved": True, "feedback": feedback},
        )

        from runtime.executor import execute_workflow
        execute_workflow.delay(execution.id)

        return Response(ExecutionSerializer(execution).data)
