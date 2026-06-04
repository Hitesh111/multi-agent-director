"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";

export default function NewWorkflowPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const wf = await api.createWorkflow({
        ...form,
        nodes: [{ id: "n1", type: "agent" }],
        edges: [],
      });
      router.push(`/workflows/${wf.id}/edit`);
    } catch {
      alert("Failed to create workflow");
    }
    setSaving(false);
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-bold">New Workflow</h1>
      <form onSubmit={save} className="space-y-3">
        <Field label="Name">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="input" />
        </Field>
        <Field label="Description">
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="input" />
        </Field>
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={saving} className="bg-accent hover:bg-accent-hover text-white text-sm px-4 py-1.5 rounded transition-colors disabled:opacity-50">
            {saving ? "Creating..." : "Create & Open Editor"}
          </button>
          <Link href="/workflows" className="text-sm text-zinc-400 hover:text-zinc-200 px-3 py-1.5">Cancel</Link>
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
