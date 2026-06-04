from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from apps.workflows.models import Workflow
from .state import WorkflowState
from .nodes import get_node_handler


def build_and_compile(workflow: Workflow) -> StateGraph:
    """Build a LangGraph StateGraph from a Workflow model and compile it.

    Each workflow node becomes a LangGraph node. Edges define routing.
    Conditional edges use a router function that reads node output
    and returns the next node id.
    """
    builder = StateGraph(WorkflowState)

    for node_def in workflow.nodes:
        node_id = node_def["id"]
        node_type = node_def.get("type", "agent")
        handler = get_node_handler(node_type, node_def)
        builder.add_node(node_id, handler)

    edges = workflow.edges or []
    node_ids = {n["id"] for n in workflow.nodes}

    if not edges:
        ids = list(node_ids)
        for i in range(len(ids) - 1):
            builder.add_edge(ids[i], ids[i + 1])
        builder.add_edge(START, ids[0])
        builder.add_edge(ids[-1], END)
        return builder.compile(checkpointer=MemorySaver())

    start_targets = []
    end_sources = []
    outgoing = {n["id"]: [] for n in workflow.nodes}

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        condition = edge.get("condition")

        if src not in node_ids or tgt not in node_ids:
            continue

        if condition:
            label = edge.get("label", "")
            outgoing.setdefault(src, []).append(("conditional", tgt, condition, label))
        else:
            outgoing[src].append(("direct", tgt))

    for nid in node_ids:
        if not any(nid == e["target"] for e in edges):
            start_targets.append(nid)
        if not any(nid == e["source"] for e in edges):
            end_sources.append(nid)

    for nid, targets in outgoing.items():
        directs = []
        conditionals = []
        for entry in targets:
            if entry[0] == "direct":
                directs.append(entry[1])
            elif entry[0] == "conditional":
                _, tgt, cond, lbl = entry
                conditionals.append((tgt, cond, lbl))

        if directs:
            for t in directs:
                builder.add_edge(nid, t)
        elif conditionals:
            def make_router(conditions):
                def router(state: WorkflowState) -> str:
                    node_output = state["node_results"].get(state["completed_nodes"][-1], "")
                    for target, cond, label in conditions:
                        if cond.lower() in str(node_output).lower():
                            return target if target in node_ids else END
                    return conditions[0][0] if conditions[0][0] in node_ids else END
                return router
            builder.add_conditional_edges(nid, make_router(conditionals), {c[0]: c[0] for c in conditionals})

    if start_targets:
        for t in start_targets:
            builder.add_edge(START, t)
    elif node_ids:
        builder.add_edge(START, list(node_ids)[0])

    if end_sources:
        for s in end_sources:
            builder.add_edge(s, END)
    elif node_ids:
        builder.add_edge(list(node_ids)[-1], END)

    return builder.compile(checkpointer=MemorySaver())
