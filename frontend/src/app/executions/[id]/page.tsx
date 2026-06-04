"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import type { Execution, Message } from "@/lib/types";
import { connectExecutionSse, type SseEvent } from "@/lib/sse";
import { useRouter } from "next/navigation";

export default async function ExecutionDetailPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <ExecutionDetail executionId={Number(id)} />;
}

function ExecutionDetail({ executionId }: { executionId: number }) {
  const router = useRouter();
  const [exec, setExec] = useState<Execution | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [liveEvents, setLiveEvents] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [submittingApproval, setSubmittingApproval] = useState(false);
  const logEnd = useRef<HTMLDivElement>(null);
  const nextMsgId = useRef(0);

  useEffect(() => {
    setError(null);
    api.getExecution(executionId).then(setExec, () => setError("Failed to load execution"));
    api.listMessages(`?execution=${executionId}`).then(
      (r) => { setMessages(r.results); nextMsgId.current = r.results.length + 1; },
      () => {},
    );
  }, [executionId]);

  const addLog = useCallback((line: string) => {
    setLiveEvents((prev) => [...prev.slice(-199), line]);
  }, []);

  useEffect(() => {
    const sse = connectExecutionSse(executionId, (event: SseEvent) => {
      const ts = new Date().toLocaleTimeString();
      switch (event.type) {
        case "node.status":
          addLog(`[${ts}] Node ${event.data.node_id}: ${event.data.status}`);
          setExec((prev) => {
            if (!prev) return prev;
            const nodeStates = (prev.node_states || []).map((ns) =>
              ns.node_id === event.data.node_id ? { ...ns, status: event.data.status } : ns,
            );
            return { ...prev, node_states: nodeStates };
          });
          break;
        case "execution.started":
          addLog(`[${ts}] Execution started — ${event.data.workflow_name}`);
          setExec((prev) => prev ? { ...prev, status: "running" } : prev);
          break;
        case "execution.completed":
          addLog(`[${ts}] Execution completed`);
          setExec((prev) => prev ? { ...prev, status: "completed", output_data: event.data.output_data as Record<string, unknown> | null } : prev);
          break;
        case "execution.failed":
          addLog(`[${ts}] Execution failed: ${event.data.error}`);
          setExec((prev) => prev ? { ...prev, status: "failed", error_message: event.data.error } : prev);
          break;
        case "execution.approved":
          addLog(`[${ts}] Execution ${event.data.approved ? "approved" : "rejected"} — ${event.data.feedback || "no feedback"}`);
          if (event.data.approved) {
            setExec((prev) => prev ? { ...prev, status: "running" } : prev);
          }
          break;
        case "message.created": {
          addLog(`[${ts}] ${event.data.agent_name}: ${event.data.content.slice(0, 100)}`);
          const msg: Message = {
            id: nextMsgId.current++,
            execution: executionId,
            source_agent: 0,
            source_agent_name: event.data.agent_name,
            role: event.data.role,
            content: event.data.content,
            token_count: event.data.token_count,
            channel: "web",
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, msg]);
          break;
        }
      }
    });

    return () => sse.close();
  }, [executionId, addLog]);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveEvents]);

  async function handleCancel() {
    setCancelling(true);
    try {
      const updated = await api.cancelExecution(executionId);
      setExec(updated);
      addLog(`[${new Date().toLocaleTimeString()}] Execution cancelled by user`);
    } catch {
      alert("Failed to cancel execution");
    }
    setCancelling(false);
  }

  async function handleApprove() {
    setSubmittingApproval(true);
    try {
      const updated = await api.approveExecution(executionId, true, feedback);
      setExec(updated);
      addLog(`[${new Date().toLocaleTimeString()}] Execution approved — resuming`);
      setFeedback("");
    } catch {
      alert("Failed to approve execution");
    }
    setSubmittingApproval(false);
  }

  async function handleReject() {
    setSubmittingApproval(true);
    try {
      const updated = await api.approveExecution(executionId, false, feedback);
      setExec(updated);
      addLog(`[${new Date().toLocaleTimeString()}] Execution rejected`);
      setFeedback("");
    } catch {
      alert("Failed to reject execution");
    }
    setSubmittingApproval(false);
  }

  function handleRerun() {
    router.push(`/workflows`);
  }

  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!exec) return <p className="text-zinc-500 text-sm">Loading...</p>;

  const outputData = (exec.output_data || {}) as Record<string, unknown>;
  let finalOutputText = "";
  if (outputData.content) {
    finalOutputText = String(outputData.content);
  } else if (outputData.result) {
    finalOutputText = String(outputData.result);
  } else if (outputData.narrative) {
    finalOutputText = String(outputData.narrative);
  } else if (outputData.node_results) {
    const nodeResults = outputData.node_results as Record<string, string>;
    const keys = Object.keys(nodeResults);
    if (keys.length > 0) {
      const lastKey = keys[keys.length - 1];
      finalOutputText = nodeResults[lastKey];
    }
  }

  const sceneImage = outputData.scene_image as string | undefined;
  const isRunning = exec.status === "running" || exec.status === "pending";
  const isTerminal = exec.status === "completed" || exec.status === "failed" || exec.status === "cancelled";
  const isAwaitingApproval = exec.status === "needs_approval";

  const tokens = exec.token_usage || {};
  const promptTokens = tokens.prompt_tokens || 0;
  const completionTokens = tokens.completion_tokens || 0;
  const totalTokens = tokens.total_tokens || (promptTokens + completionTokens);
  const estimatedCost = ((promptTokens * 0.15) + (completionTokens * 0.60)) / 1_000_000;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Execution #{executionId}</h1>
          <p className="text-sm text-zinc-400 mt-1">{exec.workflow_name || `Workflow ${exec.workflow}`}</p>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="bg-yellow-700 hover:bg-yellow-600 text-white text-sm px-3 py-1.5 rounded transition-colors disabled:opacity-50"
            >
              {cancelling ? "Cancelling..." : "Cancel"}
            </button>
          )}
          {isTerminal && (
            <button
              onClick={handleRerun}
              className="bg-accent hover:bg-accent-hover text-white text-sm px-3 py-1.5 rounded transition-colors"
            >
              Rerun
            </button>
          )}
          <span className={`text-sm px-3 py-1 rounded ${statusBadge(exec.status)}`}>
            {exec.status}
          </span>
        </div>
      </div>

      {/* Node States Graph */}
      {exec.node_states && exec.node_states.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Node Execution Graph</h2>
          <div className="flex flex-wrap gap-2">
            {exec.node_states.map((ns) => (
              <div key={ns.id} className={`flex items-center gap-2 px-3 py-2 rounded border text-xs ${nodeStatusStyle(ns.status)}`}>
                <span className="font-medium">{ns.node_id}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${nodeDotStyle(ns.status)}`}>
                  {ns.status === "running" ? "..." : ns.status}
                </span>
                {ns.started_at && ns.completed_at && (
                  <span className="text-zinc-500">
                    {Math.round((new Date(ns.completed_at).getTime() - new Date(ns.started_at).getTime()) / 1000)}s
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input / Output */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-lg p-4 space-y-3">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Input Prompt</h2>
          <div className="text-sm text-zinc-200 whitespace-pre-wrap break-words bg-zinc-900/40 p-3 rounded border border-zinc-800">
            {typeof exec.input_data === "object" && exec.input_data
              ? String((exec.input_data as Record<string, unknown>).text || (exec.input_data as Record<string, unknown>).user_input || JSON.stringify(exec.input_data))
              : String(exec.input_data)}
          </div>
          {typeof exec.input_data === "object" && exec.input_data && !!(exec.input_data as Record<string, unknown>).image_url && (
            <div className="space-y-1">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block">Uploaded Image Input</span>
              <img
                src={(exec.input_data as Record<string, string>).image_url}
                alt="Uploaded Input"
                className="max-h-48 rounded border border-zinc-800 object-contain bg-black max-w-full"
              />
            </div>
          )}
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-3">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Structured Output</h2>
          {finalOutputText ? (
            <div className="space-y-3">
              <div className="text-sm text-zinc-100 whitespace-pre-wrap break-words bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 font-mono leading-relaxed max-h-[300px] overflow-y-auto">
                {finalOutputText}
              </div>
              {sceneImage && (
                <div className="border border-zinc-800 rounded-lg overflow-hidden bg-zinc-900/30">
                  <img src={sceneImage} alt="Scene" className="w-full h-auto object-contain max-h-96" />
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-zinc-500 italic p-3 bg-zinc-900/20 rounded border border-dashed border-zinc-800">
              {exec.status === "completed"
                ? "No step results were recorded."
                : exec.status === "failed"
                ? `Execution failed: ${exec.error_message}`
                : "Outputs will appear here when the execution finishes."}
            </div>
          )}
        </div>
      </div>

      {/* Token Usage & Cost */}
      {totalTokens > 0 && (
        <div className="bg-card border border-border rounded-lg p-3">
          <h2 className="text-xs font-semibold text-zinc-400 mb-2">Token Usage & Cost</h2>
          <div className="flex flex-wrap gap-4 text-sm">
            <span>Prompt: <strong>{promptTokens.toLocaleString()}</strong></span>
            <span>Completion: <strong>{completionTokens.toLocaleString()}</strong></span>
            <span>Total: <strong>{totalTokens.toLocaleString()}</strong></span>
            <span className="text-zinc-600">|</span>
            <span>Est. Cost: <strong className="text-emerald-400">${estimatedCost.toFixed(5)}</strong></span>
          </div>
        </div>
      )}

      {/* Human Approval */}
      {isAwaitingApproval && (
        <div className="bg-card border border-amber-500/30 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <h2 className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Awaiting Your Approval</h2>
          </div>
          <p className="text-sm text-zinc-400">
            The AI has produced a draft. Review it above, then approve or reject it.
          </p>
          <div className="space-y-2">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Optional feedback for the AI..."
              className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-sm text-zinc-200 placeholder-zinc-600 resize-none h-20"
            />
            <div className="flex gap-2">
              <button
                onClick={handleApprove}
                disabled={submittingApproval}
                className="bg-emerald-700 hover:bg-emerald-600 text-white text-sm px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                {submittingApproval ? "Submitting..." : "Approve & Continue"}
              </button>
              <button
                onClick={handleReject}
                disabled={submittingApproval}
                className="bg-red-800 hover:bg-red-700 text-white text-sm px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                {submittingApproval ? "Submitting..." : "Reject"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Live Log */}
      <div className="bg-card border border-border rounded-lg p-3">
        <h2 className="text-xs font-semibold text-zinc-400 mb-2">Live Log</h2>
        <div className="bg-black rounded p-3 h-48 overflow-y-auto text-xs font-mono text-zinc-400 space-y-0.5">
          {liveEvents.length === 0 && <span className="text-zinc-600">Waiting for events...</span>}
          {liveEvents.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
          <div ref={logEnd} />
        </div>
      </div>

      {/* Messages */}
      <div className="bg-card border border-border rounded-lg p-3">
        <h2 className="text-xs font-semibold text-zinc-400 mb-2">Messages ({messages.length})</h2>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {messages.map((m) => (
            <div key={m.id} className="border border-border rounded p-2 text-sm">
              <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
                <span className={m.role === "assistant" ? "text-accent" : "text-emerald-400"}>
                  {m.role}
                </span>
                <span>{m.source_agent_name || `Agent ${m.source_agent}`}</span>
                <span>{m.token_count > 0 && `${m.token_count} tokens`}</span>
              </div>
              <div className="text-zinc-300 whitespace-pre-wrap break-words">{m.content}</div>
            </div>
          ))}
          {messages.length === 0 && (
            <p className="text-xs text-zinc-600">No messages yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function statusBadge(s: string) {
  const map: Record<string, string> = {
    pending: "bg-zinc-800 text-zinc-300",
    running: "bg-blue-900 text-blue-200",
    completed: "bg-emerald-900 text-emerald-200",
    failed: "bg-red-900 text-red-200",
    cancelled: "bg-yellow-900 text-yellow-200",
    needs_approval: "bg-amber-900 text-amber-200",
  };
  return map[s] || "bg-zinc-800 text-zinc-300";
}

function nodeStatusStyle(s: string) {
  const map: Record<string, string> = {
    pending: "border-zinc-800 bg-zinc-900/30 text-zinc-400",
    running: "border-blue-800 bg-blue-900/20 text-blue-300",
    completed: "border-emerald-800 bg-emerald-900/20 text-emerald-300",
    failed: "border-red-800 bg-red-900/20 text-red-300",
    cancelled: "border-yellow-800 bg-yellow-900/20 text-yellow-300",
    needs_approval: "border-amber-800 bg-amber-900/20 text-amber-300",
  };
  return map[s] || "border-zinc-800 bg-zinc-900/30 text-zinc-400";
}

function nodeDotStyle(s: string) {
  const map: Record<string, string> = {
    pending: "bg-zinc-700 text-zinc-300",
    running: "bg-blue-800 text-blue-200",
    completed: "bg-emerald-800 text-emerald-200",
    failed: "bg-red-800 text-red-200",
    cancelled: "bg-yellow-800 text-yellow-200",
    needs_approval: "bg-amber-800 text-amber-200",
  };
  return map[s] || "bg-zinc-700 text-zinc-300";
}
