"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Execution } from "@/lib/types";
import Link from "next/link";

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.listExecutions().then((r) => {
      setExecutions(r.results);
      setLoading(false);
    });
  }, []);

  const filtered = executions.filter((e) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      String(e.id).includes(q) ||
      (e.workflow_name || "").toLowerCase().includes(q) ||
      e.status.includes(q) ||
      (e.error_message || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Executions</h1>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search executions..."
          className="input max-w-xs text-sm"
        />
      </div>

      {loading && <p className="text-zinc-500 text-sm">Loading...</p>}

      <div className="space-y-2">
        {filtered.map((e) => (
          <Link
            key={e.id}
            href={`/executions/${e.id}`}
            className="block bg-card border border-border rounded-lg p-4 hover:border-accent/50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-sm">
                  Execution #{e.id}
                  <span className="text-zinc-500 font-normal ml-2">
                    {e.workflow_name || `Workflow ${e.workflow}`}
                  </span>
                </div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                </div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${statusBadge(e.status)}`}>
                {e.status}
              </span>
            </div>
            {e.error_message && (
              <div className="text-xs text-red-400 mt-2 truncate">{e.error_message}</div>
            )}
          </Link>
        ))}
        {!loading && filtered.length === 0 && (
          <p className="text-zinc-500 text-sm">{search ? "No executions match your search." : "No executions yet."}</p>
        )}
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
  };
  return map[s] || "bg-zinc-800 text-zinc-300";
}
