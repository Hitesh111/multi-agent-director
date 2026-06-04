"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import type { Execution } from "@/lib/types";
import { Bot, Workflow as WfIcon, Play, Plus } from "lucide-react";
import Link from "next/link";

interface DashboardStats {
  agents: number;
  workflows: number;
  executions: number;
  execution_statuses: Record<string, number>;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentExecs, setRecentExecs] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getStats().then(setStats, () => {}),
      api.listExecutions("?ordering=-created_at").then(
        (r) => setRecentExecs(r.results || []), () => {},
      ),
    ]).finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      label: "Agents",
      count: stats?.agents ?? 0,
      icon: Bot,
      href: "/agents",
      color: "text-sky-400",
      empty: "No agents yet. Create your first agent.",
    },
    {
      label: "Workflows",
      count: stats?.workflows ?? 0,
      icon: WfIcon,
      href: "/workflows",
      color: "text-violet-400",
      empty: "No workflows yet. Create your first workflow.",
    },
    {
      label: "Executions",
      count: stats?.executions ?? 0,
      icon: Play,
      href: "/executions",
      color: "text-emerald-400",
      empty: "No executions yet.",
    },
  ];

  const statusCounts = stats?.execution_statuses ?? {};

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold">Dashboard</h1>
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border rounded-lg p-4 animate-pulse">
              <div className="h-4 bg-zinc-800 rounded w-16 mb-3" />
              <div className="h-8 bg-zinc-800 rounded w-12" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-3 gap-4">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.label}
              href={c.href}
              className="bg-card border border-border rounded-lg p-4 hover:border-accent/50 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-400">{c.label}</span>
                <Icon className={`w-5 h-5 ${c.color}`} />
              </div>
              <div className="text-2xl font-bold">{c.count}</div>
              {c.count === 0 && (
                <div className="text-xs text-zinc-600 mt-2">{c.empty}</div>
              )}
            </Link>
          );
        })}
      </div>

      {stats && stats.executions > 0 && (
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="text-sm font-semibold mb-3">Execution Status</h2>
          <div className="flex gap-4 text-sm">
            {["pending", "running", "completed", "failed", "cancelled"].map((s) => (
              <div key={s} className="flex items-center gap-1">
                <span className="text-zinc-500 capitalize">{s}:</span>
                <span className="font-bold">{statusCounts[s] || 0}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Recent Executions</h2>
          <Link href="/executions" className="text-xs text-accent hover:underline">
            View all
          </Link>
        </div>
        <div className="space-y-2">
          {recentExecs.map((e) => (
            <Link
              key={e.id}
              href={`/executions/${e.id}`}
              className="block bg-card border border-border rounded p-3 hover:border-accent/50 transition-colors"
            >
              <div className="flex items-center justify-between text-sm">
                <span>
                  Execution #{e.id}
                  <span className="text-zinc-500 ml-2">{e.workflow_name || `WF ${e.workflow}`}</span>
                </span>
                <span className={`text-xs px-2 py-0.5 rounded ${statusBadge(e.status)}`}>
                  {e.status}
                </span>
              </div>
            </Link>
          ))}
            {recentExecs.length === 0 && stats?.executions === 0 && (
            <p className="text-sm text-zinc-500">
              No executions yet. Create a workflow and trigger it.
            </p>
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
  };
  return map[s] || "bg-zinc-800 text-zinc-300";
}
