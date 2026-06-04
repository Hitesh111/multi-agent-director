"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";
import Link from "next/link";
import { Plus, Edit2, Trash2 } from "lucide-react";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await api.listAgents();
      setAgents(r.results);
    } catch {
      // handled — show empty list
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function remove(id: number) {
    if (!confirm("Delete this agent?")) return;
    await api.deleteAgent(id);
    load();
  }

  const filtered = agents.filter((a) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      a.name.toLowerCase().includes(q) ||
      a.role.toLowerCase().includes(q) ||
      a.provider.includes(q) ||
      (a.model || "").includes(q)
    );
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Agents</h1>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents..."
            className="input max-w-xs text-sm"
          />
          <Link
            href="/agents/new"
            className="flex items-center gap-1 bg-accent hover:bg-accent-hover text-white text-sm px-3 py-1.5 rounded transition-colors"
          >
            <Plus className="w-4 h-4" /> New Agent
          </Link>
        </div>
      </div>

      {loading && <p className="text-zinc-500 text-sm">Loading...</p>}

      <div className="grid gap-3">
        {filtered.map((a) => (
          <div key={a.id} className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
            <div>
              <Link href={`/agents/${a.id}`} className="font-semibold text-sm hover:text-accent transition-colors">{a.name}</Link>
              <div className="text-xs text-zinc-500 mt-0.5">
                {a.provider} / {a.model || "default"} &middot; {a.role || "no role"}
              </div>
              {a.tools && a.tools.length > 0 && (
                <div className="text-xs text-zinc-600 mt-0.5">
                  Tools: {a.tools.join(", ")}
                </div>
              )}
              {a.enabled_channels?.length > 0 && (
                <div className="text-xs text-zinc-600 mt-0.5">
                  Channels: {a.enabled_channels.join(", ")}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded ${a.is_active ? "bg-emerald-900 text-emerald-200" : "bg-zinc-800 text-zinc-500"}`}>
                {a.is_active ? "active" : "inactive"}
              </span>
              <Link href={`/agents/${a.id}/edit`} className="text-zinc-400 hover:text-accent transition-colors" title="Edit">
                <Edit2 className="w-4 h-4" />
              </Link>
              <button onClick={() => remove(a.id)} className="text-zinc-400 hover:text-red-400 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {!loading && filtered.length === 0 && (
          <p className="text-zinc-500 text-sm">{search ? "No agents match your search." : "No agents yet."}</p>
        )}
      </div>
    </div>
  );
}
