import pytest
from langgraph.graph.state import CompiledStateGraph

from apps.workflows.models import Workflow
from runtime.graph import build_and_compile, WorkflowState


@pytest.mark.django_db
class TestGraphBuilder:
    def test_builds_state_graph(self):
        wf = Workflow.objects.create(
            name="TestWF",
            nodes=[
                {"id": "n1", "type": "agent"},
                {"id": "n2", "type": "agent"},
            ],
            edges=[{"source": "n1", "target": "n2"}],
        )
        graph = build_and_compile(wf)
        assert isinstance(graph, CompiledStateGraph)

    def test_single_node_workflow(self):
        wf = Workflow.objects.create(
            name="SingleNode",
            nodes=[{"id": "only", "type": "agent"}],
            edges=[],
        )
        graph = build_and_compile(wf)
        assert graph is not None

    def test_conditional_edge(self):
        wf = Workflow.objects.create(
            name="ConditionalWF",
            nodes=[
                {"id": "classify", "type": "agent"},
                {"id": "approve", "type": "agent"},
                {"id": "reject", "type": "agent"},
            ],
            edges=[
                {
                    "source": "classify",
                    "target": "approve",
                    "condition": "approved",
                    "label": "approved",
                },
                {
                    "source": "classify",
                    "target": "reject",
                    "condition": "rejected",
                    "label": "rejected",
                },
            ],
        )
        graph = build_and_compile(wf)
        assert graph is not None

    def test_disconnected_nodes_auto_wired(self):
        wf = Workflow.objects.create(
            name="NoEdges",
            nodes=[
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "agent"},
            ],
            edges=[],
        )
        graph = build_and_compile(wf)
        assert graph is not None
