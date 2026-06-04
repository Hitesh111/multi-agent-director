"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Agent, Workflow } from "@/lib/types";
import type { Node, Edge } from "reactflow";
import { MarkerType, useNodesState, useEdgesState } from "reactflow";
import dynamic from "next/dynamic";

const WorkflowCanvas = dynamic(() => import("@/components/flow/WorkflowCanvas"), {
  ssr: false,
  loading: () => <p className="text-zinc-500 text-sm">Loading editor...</p>,
});

export default async function EditWorkflowPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <EditWorkflowForm workflowId={Number(id)} />;
}

function EditWorkflowForm({ workflowId }: { workflowId: number }) {
  const router = useRouter();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [name, setName] = useState("");
  const [nodes, setNodes, onNodesChange] = useNodesState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);

  useEffect(() => {
    api.getWorkflow(workflowId).then((wf) => {
      setWorkflow(wf);
      setName(wf.name);
      setNodes(toNodes(wf));
      setEdges(toEdges(wf));
    }, () => {});
    api.listAgents().then((r) => setAgents(r.results), () => {});
  }, [workflowId]);

  const handleSave = useCallback(
    async (nodes: Node[], edges: Edge[]) => {
      setSaving(true);
      try {
        const wfNodes = nodes.map((n) => ({
          id: n.id,
          type: n.data.nodeType || "agent",
          position: { x: n.position.x, y: n.position.y },
          data: { agentId: n.data.agentId },
          agentId: n.data.agentId,
        }));
        const wfEdges = edges.map((e) => ({
          source: e.source,
          target: e.target,
          label: typeof e.label === "string" ? e.label : "",
          condition: (e.data as Record<string, unknown>)?.condition as string || "",
        }));
        await api.updateWorkflow(workflowId, {
          name,
          nodes: wfNodes as any,
          edges: wfEdges,
        });
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } catch {
        alert("Failed to save workflow");
      }
      setSaving(false);
    },
    [workflowId, name],
  );

  if (!workflow) return <p className="text-zinc-500 text-sm">Loading...</p>;

  return (
    <div className="space-y-3 h-full flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">Edit: {workflow.name}</h1>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input max-w-xs"
            placeholder="Workflow name"
          />
        </div>
        <div className="flex items-center gap-2">
          {saved && <span className="text-xs text-emerald-400">Saved!</span>}
          <button
            onClick={() => handleSave(nodes, edges)}
            disabled={saving}
            className="bg-accent hover:bg-accent-hover text-white text-sm px-3 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <WorkflowCanvas
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        setNodes={setNodes}
        setEdges={setEdges}
        agents={agents}
      />
    </div>
  );
}

const toNodes = (wf: Workflow): Node[] =>
  (wf.nodes || []).map((n, i) => ({
    id: n.id,
    type: "default",
    position: (n as any).position || { x: 100 + i * 220, y: 200 },
    data: {
      label: n.type === "agent" ? `Agent: ${n.data?.agentId || "unset"}` : n.type,
      nodeType: n.type,
      agentId: n.agentId || n.data?.agentId,
    },
    style: nodeStyle(n.type),
  }));

const toEdges = (wf: Workflow): Edge[] =>
  (wf.edges || []).map((e) => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: e.label || e.condition || "",
    data: { condition: e.condition || "" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
    style: { stroke: "#6366f1", strokeWidth: 2 },
  }));

function nodeStyle(type: string): React.CSSProperties {
  const colors: Record<string, string> = {
    agent: "#6366f1",
    human_approval: "#f59e0b",
    input: "#10b981",
    output: "#ef4444",
  };
  return {
    background: "#18181b",
    border: `1px solid ${colors[type] || "#6366f1"}`,
    color: "#e4e4e7",
    borderRadius: 8,
    padding: "8px 16px",
    fontSize: 12,
    minWidth: 140,
  };
}
