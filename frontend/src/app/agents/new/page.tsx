"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";
import Link from "next/link";

export default function NewAgentPage() {
  const router = useRouter();
  const [form, setForm] = useState<{
    name: string;
    role: string;
    system_prompt: string;
    provider: Agent["provider"];
    model: string;
    temperature: number;
    max_iterations: number;
    memory_enabled: boolean;
    enabled_channels: string;
    tools: string;
    skills: string;
    schedule_config: string;
    interaction_rules: string;
    allowed_agents: string;
    is_active: boolean;
  }>({
    name: "",
    role: "",
    system_prompt: "",
    provider: "deepseek" as Agent["provider"],
    model: "",
    temperature: 0.7,
    max_iterations: 10,
    memory_enabled: true,
    enabled_channels: "",
    tools: "",
    skills: "",
    schedule_config: "",
    interaction_rules: "",
    allowed_agents: "",
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      let parsedSchedule = null;
      let parsedRules = null;
      try { parsedSchedule = form.schedule_config ? JSON.parse(form.schedule_config) : null; } catch {}
      try { parsedRules = form.interaction_rules ? JSON.parse(form.interaction_rules) : {}; } catch {}
      await api.createAgent({
        ...form,
        temperature: Number(form.temperature),
        max_iterations: Number(form.max_iterations),
        enabled_channels: form.enabled_channels
          ? form.enabled_channels.split(",").map((s: string) => s.trim())
          : [],
        tools: form.tools
          ? form.tools.split(",").map((s: string) => s.trim())
          : [],
        skills: form.skills
          ? form.skills.split(",").map((s: string) => s.trim())
          : [],
        schedule_config: parsedSchedule,
        interaction_rules: parsedRules,
        allowed_agents: form.allowed_agents
          ? form.allowed_agents.split(",").map((s: string) => Number(s.trim())).filter((n: number) => !isNaN(n))
          : [],
      });
      router.push("/agents");
    } catch (err) {
      alert("Failed to create agent");
    }
    setSaving(false);
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-bold">New Agent</h1>
      <form onSubmit={save} className="space-y-3">
        <Field label="Name">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="input" />
        </Field>
        <Field label="Role">
          <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input" />
        </Field>
        <Field label="System Prompt">
          <textarea value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} rows={4} className="input" />
        </Field>
        <Field label="Provider">
          <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value as Agent["provider"] })} className="input">
            <option value="deepseek">DeepSeek</option>
            <option value="grok">Grok (Groq)</option>
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="opencode">OpenCode</option>
          </select>
        </Field>
        <Field label="Model (optional)">
          <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="deepseek-chat" className="input" />
        </Field>
        <Field label="Tools (comma-separated)">
          <input value={form.tools} onChange={(e) => setForm({ ...form, tools: e.target.value })} placeholder="web_search, calculator, code_executor" className="input" />
        </Field>
        <Field label="Skills (comma-separated)">
          <input value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} placeholder="research, summarization, coding, analysis" className="input" />
        </Field>
        <Field label="Allowed Agent IDs (comma-separated, leave empty for all)">
          <input value={form.allowed_agents} onChange={(e) => setForm({ ...form, allowed_agents: e.target.value })} placeholder="1, 2, 3" className="input" />
        </Field>
        <Field label="Schedule Config (JSON)">
          <textarea value={form.schedule_config} onChange={(e) => setForm({ ...form, schedule_config: e.target.value })} rows={2} placeholder='{"cron": "0 */6 * * *"}' className="input" />
        </Field>
        <Field label="Interaction Rules / Guardrails (JSON)">
          <textarea value={form.interaction_rules} onChange={(e) => setForm({ ...form, interaction_rules: e.target.value })} rows={2} placeholder='{"max_turns": 10, "allowed_topics": ["dnd"]}' className="input" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Temperature">
            <input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Max Iterations">
            <input type="number" min="1" value={form.max_iterations} onChange={(e) => setForm({ ...form, max_iterations: Number(e.target.value) })} className="input" />
          </Field>
        </div>
        <Field label="Enabled Channels (comma-separated)">
          <input value={form.enabled_channels} onChange={(e) => setForm({ ...form, enabled_channels: e.target.value })} placeholder="telegram, web" className="input" />
        </Field>
        <Field label="Memory Enabled">
          <input type="checkbox" checked={form.memory_enabled} onChange={(e) => setForm({ ...form, memory_enabled: e.target.checked })} className="accent-accent" />
        </Field>
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={saving} className="bg-accent hover:bg-accent-hover text-white text-sm px-4 py-1.5 rounded transition-colors disabled:opacity-50">
            {saving ? "Saving..." : "Create Agent"}
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
