"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent, Message } from "@/lib/types";
import Link from "next/link";
import { Edit2 } from "lucide-react";

export default async function AgentDetailPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <AgentDetail agentId={Number(id)} />;
}

function AgentDetail({ agentId }: { agentId: number }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [memory, setMemory] = useState<Message[]>([]);

  useEffect(() => {
    api.getAgent(agentId).then(setAgent, () => setError("Agent not found"));
    api.listMessages(`?source_agent=${agentId}`).then((res) => setMemory(res.results.slice(-10)), () => {});
  }, [agentId]);

  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!agent) return <p className="text-zinc-500 text-sm">Loading...</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{agent.name}</h1>
          <p className="text-sm text-zinc-400 mt-1">{agent.role || "No role specified"}</p>
        </div>
        <Link
          href={`/agents/${agent.id}/edit`}
          className="flex items-center gap-1 bg-accent hover:bg-accent-hover text-white text-sm px-3 py-1.5 rounded transition-colors"
        >
          <Edit2 className="w-4 h-4" /> Edit
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-lg p-4 space-y-2">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Configuration</h2>
          <DetailRow label="Provider" value={agent.provider} />
          <DetailRow label="Model" value={agent.model || "default"} />
          <DetailRow label="Temperature" value={String(agent.temperature)} />
          <DetailRow label="Max Iterations" value={String(agent.max_iterations)} />
          <DetailRow label="Status" value={agent.is_active ? "Active" : "Inactive"} />
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-2">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Capabilities</h2>
          <DetailRow label="Memory" value={agent.memory_enabled ? "Enabled" : "Disabled"} />
          <DetailRow label="Skills" value={agent.skills?.length ? agent.skills.join(", ") : "None"} />
          <DetailRow label="Tools" value={agent.tools?.length ? agent.tools.join(", ") : "None"} />
          <DetailRow label="Channels" value={agent.enabled_channels?.length ? agent.enabled_channels.join(", ") : "None"} />
        </div>

        {agent.schedule_config && Object.keys(agent.schedule_config).length > 0 && (
          <div className="bg-card border border-border rounded-lg p-4 space-y-2">
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Schedule</h2>
            <DetailRow label="Interval" value={agent.schedule_config.interval_minutes ? `Every ${String(agent.schedule_config.interval_minutes)} min` : "—"} />
            <DetailRow label="Cron" value={String(agent.schedule_config.cron || "—")} />
            {!!agent.schedule_config.last_fired_at && (
              <DetailRow label="Last Fired" value={new Date(String(agent.schedule_config.last_fired_at)).toLocaleString()} />
            )}
          </div>
        )}
      </div>

      <div className="bg-card border border-border rounded-lg p-4 space-y-2">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">System Prompt</h2>
        <div className="text-sm text-zinc-300 whitespace-pre-wrap break-words bg-zinc-900/40 p-3 rounded border border-zinc-800 max-h-64 overflow-y-auto">
          {agent.system_prompt || "No system prompt set."}
        </div>
      </div>

      {memory.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4 space-y-2">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Recent Memory</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {memory.map((m) => (
              <div key={m.id} className="text-sm border-l-2 border-zinc-700 pl-3 py-1">
                <div className="text-xs text-zinc-500 mb-0.5">{m.role} &middot; {new Date(m.created_at).toLocaleString()}</div>
                <div className="text-zinc-300 whitespace-pre-wrap break-words">{m.content.slice(0, 300)}{m.content.length > 300 ? "..." : ""}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {agent.interaction_rules && Object.keys(agent.interaction_rules).length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4 space-y-2">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Guardrails</h2>
          {!!agent.interaction_rules.max_turns && <DetailRow label="Max Turns" value={String(agent.interaction_rules.max_turns)} />}
          {!!agent.interaction_rules.max_response_length && <DetailRow label="Max Response Length" value={String(agent.interaction_rules.max_response_length)} />}
          {Array.isArray(agent.interaction_rules.allowed_topics) && agent.interaction_rules.allowed_topics.length > 0 && (
            <DetailRow label="Allowed Topics" value={(agent.interaction_rules.allowed_topics as string[]).join(", ")} />
          )}
        </div>
      )}

      <div className="text-xs text-zinc-500">
        Created: {new Date(agent.created_at).toLocaleString()} &middot;
        Updated: {new Date(agent.updated_at).toLocaleString()}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-200 font-medium">{value}</span>
    </div>
  );
}
