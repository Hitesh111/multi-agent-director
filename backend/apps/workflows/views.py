from django.utils import timezone

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Workflow
from .serializers import WorkflowSerializer
from apps.executions.models import Execution, ExecutionNode
from apps.executions.serializers import ExecutionSerializer
from apps.agents.models import Agent
from runtime.executor import execute_workflow


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]

    @action(detail=True, methods=["post"])
    def trigger(self, request, pk=None):
        workflow = self.get_object()
        if not workflow.is_active:
            return Response({"error": "Workflow is inactive"}, status=400)

        input_data = request.data.get("input_data", {})
        node_defs = {n["id"]: n for n in workflow.nodes}

        execution = Execution.objects.create(
            workflow=workflow,
            status=Execution.Status.RUNNING,
            started_at=timezone.now(),
            input_data=input_data,
        )

        for node in workflow.nodes:
            agent_id = node.get("agentId") or node.get("data", {}).get("agentId")
            agent = Agent.objects.filter(id=agent_id).first() if agent_id else None
            ExecutionNode.objects.create(
                execution=execution,
                node_id=node["id"],
                agent=agent,
                status=Execution.Status.PENDING,
                input_data=input_data,
            )

        execute_workflow.delay(execution.id)

        serializer = ExecutionSerializer(execution)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=["post"])
    def deploy_template(self, request):
        """Deploy the seeded templates and return the requested workflow."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("seed_demo", stdout=out)
        output = out.getvalue()

        template_name = request.data.get("template_name", "Research → Summarize → Review")
        workflow = Workflow.objects.filter(
            name=template_name
        ).first()

        if not workflow:
            workflow = Workflow.objects.filter(
                name="Research → Summarize → Review"
            ).first()

        return Response({
            "message": "Template deployed successfully",
            "output": output,
            "workflow_id": workflow.id if workflow else None,
        })
