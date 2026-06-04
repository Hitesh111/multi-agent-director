"use client";

import { useCallback, useRef, useState } from "react";
import ReactFlow, {
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  Controls,
  Background,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import type { Agent } from "@/lib/types";
const nodeTypes: NodeTypes = {};

interface Props {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: any;
  onEdgesChange: any;
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  agents: Agent[];
}

let nodeCounter = 1;

export default function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  setNodes,
  setEdges,
  agents,
}: Props) {
  const agentsList = agents;
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [addMenuPos, setAddMenuPos] = useState({ x: 0, y: 0 });

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
            style: { stroke: "#6366f1", strokeWidth: 2 },
          },
          eds,
        ),
      );
    },
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/reactflow");
      if (!type || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: `${type}-${nodeCounter++}`,
        type: "default",
        position,
        data: {
          label: type === "agent" ? "Agent Node" : type === "human_approval" ? "Human Approval" : type,
          nodeType: type,
        },
        style: nodeStyle(type),
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
  }, []);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
    setShowAddMenu(false);
  }, []);

  function updateNodeData(nodeId: string, data: Record<string, unknown>) {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n,
      ),
    );
  }

  function updateEdgeData(edgeId: string, data: Record<string, unknown>) {
    setEdges((eds) =>
      eds.map((e) =>
        e.id === edgeId ? { ...e, ...data } : e,
      ),
    );
  }

  function deleteSelectedNode() {
    if (!selectedNode) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
    setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
  }

  function deleteSelectedEdge() {
    if (!selectedEdge) return;
    setEdges((eds) => eds.filter((e) => e.id !== selectedEdge.id));
    setSelectedEdge(null);
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-120px)]">
      {/* Node Palette */}
      <div className="w-48 bg-card border border-border rounded-lg p-3 space-y-2 shrink-0">
        <div className="text-xs font-semibold text-zinc-400 mb-2">Drag Nodes</div>
        <PaletteItem type="agent" label="Agent Node" color="#6366f1" />
        <PaletteItem type="human_approval" label="Human Approval" color="#f59e0b" />
        <PaletteItem type="input" label="Input Node" color="#10b981" />
        <PaletteItem type="output" label="Output Node" color="#ef4444" />
      </div>

      {/* Canvas */}
      <div className="flex-1 relative" ref={reactFlowWrapper}>
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <Background color="#27272a" gap={16} />
            <MiniMap
              style={{ background: "#121218" }}
              nodeColor="#27272a"
              maskColor="rgba(0,0,0,0.6)"
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {/* Node Properties Panel */}
      {selectedNode && (
        <div className="w-72 bg-card border border-border rounded-lg p-4 shrink-0 space-y-3 overflow-y-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-400">Node Properties</span>
            <button onClick={deleteSelectedNode} className="text-xs text-red-400 hover:text-red-300">Delete</button>
          </div>

          <Field label="Node ID">
            <input value={selectedNode.id} disabled className="input text-zinc-500" />
          </Field>

          <Field label="Label">
            <input
              value={selectedNode.data.label || ""}
              onChange={(e) => updateNodeData(selectedNode.id, { label: e.target.value })}
              className="input"
            />
          </Field>

          {selectedNode.data.nodeType === "agent" && (
            <Field label="Agent">
              <select
                value={selectedNode.data.agentId || ""}
                onChange={(e) => updateNodeData(selectedNode.id, { agentId: Number(e.target.value) })}
                className="input"
              >
                <option value="">Select agent...</option>
                {agentsList.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
          )}

          {selectedNode.data.nodeType === "human_approval" && (
            <Field label="Approval Required">
              <input
                type="checkbox"
                checked={selectedNode.data.requiresApproval !== false}
                onChange={(e) => updateNodeData(selectedNode.id, { requiresApproval: e.target.checked })}
                className="accent-accent"
              />
            </Field>
          )}
        </div>
      )}

      {/* Edge Properties Panel */}
      {selectedEdge && (
        <div className="w-72 bg-card border border-border rounded-lg p-4 shrink-0 space-y-3 overflow-y-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-400">Edge Properties</span>
            <button onClick={deleteSelectedEdge} className="text-xs text-red-400 hover:text-red-300">Delete</button>
          </div>

          <Field label="Edge ID">
            <input value={selectedEdge.id} disabled className="input text-zinc-500" />
          </Field>

          <Field label="From → To">
            <input value={`${selectedEdge.source} → ${selectedEdge.target}`} disabled className="input text-zinc-500" />
          </Field>

          <Field label="Label (description)">
            <input
              value={typeof selectedEdge.label === "string" ? selectedEdge.label : ""}
              onChange={(e) => updateEdgeData(selectedEdge.id, { label: e.target.value })}
              placeholder="e.g. Approved, On success"
              className="input"
            />
          </Field>

          <Field label="Condition (branching rule)">
            <textarea
              value={selectedEdge.data?.condition || (selectedEdge as any).condition || ""}
              onChange={(e) => updateEdgeData(selectedEdge.id, { data: { ...((selectedEdge as any).data || {}), condition: e.target.value } })}
              placeholder="e.g. intent == combat"
              rows={3}
              className="input"
            />
          </Field>

          <div className="text-[11px] text-zinc-500 leading-relaxed bg-zinc-900/50 rounded p-2 border border-zinc-800">
            Add conditions to create branching workflows. Edges without conditions always execute. When multiple edges have conditions, the first matching one runs.
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-zinc-500">{label}</label>
      {children}
    </div>
  );
}

function PaletteItem({ type, label, color }: { type: string; label: string; color: string }) {
  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData("application/reactflow", type);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="flex items-center gap-2 px-3 py-2 rounded text-sm cursor-grab active:cursor-grabbing border border-border hover:border-zinc-600 transition-colors"
    >
      <div className="w-3 h-3 rounded-full" style={{ background: color }} />
      <span>{label}</span>
    </div>
  );
}

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
