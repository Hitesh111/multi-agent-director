"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";
import Link from "next/link";

export default async function EditAgentPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <EditAgentForm agentId={Number(id)} />;
}

function EditAgentForm({ agentId }: { agentId: number }) {
  const router = useRouter();
  const [form, setForm] = useState<Partial<Agent> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getAgent(agentId).then(setForm, () => setForm({} as Partial<Agent>));
  }, [agentId]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    try {
      await api.updateAgent(agentId, form);
      router.push("/agents");
    } catch {
      alert("Failed to update agent");
    }
    setSaving(false);
  }

  if (!form) return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-bold">Edit Agent</h1>
      <p className="text-zinc-500 text-sm">Loading...</p>
    </div>
  );
  if (!form.id) return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-bold">Edit Agent</h1>
      <p className="text-red-400 text-sm">Agent not found</p>
    </div>
  );

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-bold">Edit Agent</h1>
      <form onSubmit={save} className="space-y-3">
        <Field label="Name">
          <input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="input" />
        </Field>
        <Field label="Role">
          <input value={form.role || ""} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input" />
        </Field>
        <Field label="System Prompt">
          <textarea value={form.system_prompt || ""} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} rows={4} className="input" />
        </Field>
        <Field label="Provider">
          <select value={form.provider || "deepseek"} onChange={(e) => setForm({ ...form, provider: e.target.value as Agent["provider"] })} className="input">
            <option value="deepseek">DeepSeek</option>
            <option value="grok">Grok (Groq)</option>
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="opencode">OpenCode</option>
          </select>
        </Field>
        <Field label="Model">
          <input value={form.model || ""} onChange={(e) => setForm({ ...form, model: e.target.value })} className="input" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Temperature">
            <input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Max Iterations">
            <input type="number" min="1" value={form.max_iterations} onChange={(e) => setForm({ ...form, max_iterations: Number(e.target.value) })} className="input" />
          </Field>
        </div>
        <Field label="Tools (comma-separated)">
          <input value={Array.isArray(form.tools) ? form.tools.join(", ") : form.tools || ""} onChange={(e) => setForm({ ...form, tools: e.target.value.split(",").map((s: string) => s.trim()) })} placeholder="web_search, calculator" className="input" />
        </Field>
        <Field label="Skills (comma-separated)">
          <input value={Array.isArray(form.skills) ? form.skills.join(", ") : form.skills || ""} onChange={(e) => setForm({ ...form, skills: e.target.value.split(",").map((s: string) => s.trim()) })} placeholder="research, summarization, coding" className="input" />
        </Field>
        <Field label="Allowed Agent IDs (comma-separated, empty = all)">
          <input value={form.allowed_agents?.join(", ") || ""} onChange={(e) => setForm({ ...form, allowed_agents: e.target.value.split(",").map((s: string) => Number(s.trim())).filter((n: number) => !isNaN(n)) })} placeholder="1, 2, 3" className="input" />
        </Field>
        <Field label="Schedule">
          <ScheduleFields config={form.schedule_config ?? null} onChange={(sc) => setForm({ ...form, schedule_config: sc })} />
        </Field>
        <Field label="Guardrails">
          <GuardrailsFields rules={form.interaction_rules ?? {}} onChange={(v) => setForm({ ...form, interaction_rules: v })} />
        </Field>
        <Field label="Enabled Channels (comma-separated)">
          <input value={Array.isArray(form.enabled_channels) ? form.enabled_channels.join(", ") : form.enabled_channels || ""} onChange={(e) => setForm({ ...form, enabled_channels: e.target.value.split(",").map((s: string) => s.trim()) })} placeholder="telegram, web" className="input" />
        </Field>
        <div className="flex items-center gap-2">
          <label className="text-xs text-zinc-400">Memory Enabled</label>
          <input type="checkbox" checked={form.memory_enabled ?? true} onChange={(e) => setForm({ ...form, memory_enabled: e.target.checked })} className="accent-accent" />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-zinc-400">Active</label>
          <input type="checkbox" checked={form.is_active ?? true} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="accent-accent" />
        </div>
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={saving} className="bg-accent hover:bg-accent-hover text-white text-sm px-4 py-1.5 rounded transition-colors disabled:opacity-50">
            {saving ? "Saving..." : "Save"}
          </button>
          <Link href="/agents" className="text-sm text-zinc-400 hover:text-zinc-200 px-3 py-1.5">Cancel</Link>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-zinc-400">{label}</label>
      {children}
    </div>
  );
}

function GuardrailsFields({ rules, onChange }: { rules: Record<string, unknown>; onChange: (v: Record<string, unknown>) => void }) {
  const [maxTurns, setMaxTurns] = useState(typeof rules.max_turns === "number" || typeof rules.max_turns === "string" ? String(rules.max_turns) : "");
  const [maxRespLen, setMaxRespLen] = useState(typeof rules.max_response_length === "number" || typeof rules.max_response_length === "string" ? String(rules.max_response_length) : "");
  const [topics, setTopics] = useState(Array.isArray(rules.allowed_topics) ? rules.allowed_topics.join(", ") : "");

  const update = (patch: Record<string, unknown>) => {
    onChange({ ...rules, ...patch });
  };

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-zinc-500">Max Turns</label>
          <input type="number" min="0" value={maxTurns} onChange={(e) => { setMaxTurns(e.target.value); const n = parseInt(e.target.value, 10); if (!isNaN(n)) update({ max_turns: n }); }} className="input w-full" placeholder="Unlimited" />
        </div>
        <div>
          <label className="text-xs text-zinc-500">Max Response Length</label>
          <input type="number" min="0" value={maxRespLen} onChange={(e) => { setMaxRespLen(e.target.value); const n = parseInt(e.target.value, 10); if (!isNaN(n)) update({ max_response_length: n }); }} className="input w-full" placeholder="No limit" />
        </div>
      </div>
      <div>
        <label className="text-xs text-zinc-500">Allowed Topics (comma-separated, empty = all)</label>
        <input value={topics} onChange={(e) => { setTopics(e.target.value); update({ allowed_topics: e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean) }); }} className="input w-full" placeholder="technology, science, gaming" />
      </div>
      <p className="text-xs text-zinc-500">Leave blank for no guardrails</p>
    </div>
  );
}

function ScheduleFields({ config, onChange }: { config: Record<string, unknown> | null; onChange: (v: Record<string, unknown> | null) => void }) {
  const enabled = !!config && Object.keys(config).length > 0;
  const initialInterval = config?.interval_minutes ?? "";
  const initialCron = config?.cron ?? "";
  const [intervalVal, setIntervalVal] = useState(typeof initialInterval === "number" || typeof initialInterval === "string" ? String(initialInterval) : "");
  const [cronVal, setCronVal] = useState(typeof initialCron === "string" ? initialCron : "");
  const [mode, setMode] = useState(typeof config?.cron === "string" && config.cron ? "cron" : "interval");

  const toggle = () => {
    if (enabled) {
      onChange(null);
    } else {
      onChange({ interval_minutes: 30 });
      setIntervalVal("30");
      setCronVal("");
      setMode("interval");
    }
  };

  const updateInterval = (val: string) => {
    setIntervalVal(val);
    const num = parseInt(val, 10);
    if (!isNaN(num) && num > 0) {
      onChange({ interval_minutes: num });
    }
  };

  const updateCron = (val: string) => {
    setCronVal(val);
    onChange({ cron: val });
  };

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm text-zinc-300">
        <input type="checkbox" checked={enabled} onChange={toggle} className="accent-accent" />
        Enable scheduled runs
      </label>
      {enabled && (
        <div className="ml-5 space-y-2 border-l-2 border-zinc-700 pl-3">
          <div className="flex gap-2 text-xs">
            <button type="button" onClick={() => setMode("interval")} className={`px-2 py-1 rounded ${mode === "interval" ? "bg-accent text-white" : "bg-zinc-800 text-zinc-400"}`}>Interval</button>
            <button type="button" onClick={() => setMode("cron")} className={`px-2 py-1 rounded ${mode === "cron" ? "bg-accent text-white" : "bg-zinc-800 text-zinc-400"}`}>Cron</button>
          </div>
          {mode === "interval" ? (
            <div className="flex items-center gap-2">
              <input type="number" min="1" value={intervalVal} onChange={(e) => updateInterval(e.target.value)} className="input w-20" placeholder="30" />
              <span className="text-xs text-zinc-500">minutes</span>
            </div>
          ) : (
            <input value={cronVal} onChange={(e) => updateCron(e.target.value)} className="input font-mono" placeholder="0 */6 * * *" />
          )}
          <p className="text-xs text-zinc-500">
            {mode === "interval" ? "Runs every N minutes" : "Cron expression (min hour dom mon dow)"}
          </p>
        </div>
      )}
    </div>
  );
}
