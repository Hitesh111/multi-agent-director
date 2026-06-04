"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Workflow } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Edit2, Trash2, Play, Workflow as WfIcon } from "lucide-react";

export default function WorkflowsPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Trigger modal state
  const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);
  const [activeWorkflowId, setActiveWorkflowId] = useState<number | null>(null);
  const [promptText, setPromptText] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await api.listWorkflows();
      setWorkflows(r.results);
    } catch {
      // handled — show empty list
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function remove(id: number) {
    if (!confirm("Delete this workflow?")) return;
    await api.deleteWorkflow(id);
    load();
  }

  function openTriggerModal(id: number) {
    setActiveWorkflowId(id);
    setPromptText("");
    setSelectedImage(null);
    setIsTriggerModalOpen(true);
  }

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = () => {
      setSelectedImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  function handleImageRemove() {
    setSelectedImage(null);
  }

  async function handleTriggerSubmit() {
    if (!activeWorkflowId) return;
    setTriggering(true);
    try {
      const payload: Record<string, unknown> = {
        text: promptText.trim() || "Triggered from dashboard"
      };
      if (selectedImage) {
        payload.image_url = selectedImage;
      }
      const exec = await api.triggerWorkflow(activeWorkflowId, payload);
      setIsTriggerModalOpen(false);
      router.push(`/executions/${exec.id}`);
    } catch {
      alert("Failed to trigger workflow");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Workflows</h1>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search workflows..."
            className="input max-w-xs text-sm"
          />
          <Link
            href="/workflows/new"
            className="flex items-center gap-1 bg-accent hover:bg-accent-hover text-white text-sm px-3 py-1.5 rounded transition-colors"
          >
            <Plus className="w-4 h-4" /> New Workflow
          </Link>
        </div>
      </div>

      {loading && <p className="text-zinc-500 text-sm">Loading...</p>}

      <div className="grid gap-3">
        {workflows
          .filter((w) => {
            if (!search) return true;
            const q = search.toLowerCase();
            return (
              w.name.toLowerCase().includes(q) ||
              (w.description || "").toLowerCase().includes(q) ||
              String(w.nodes?.length || 0).includes(q)
            );
          })
          .map((w) => (
          <div key={w.id} className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <WfIcon className="w-5 h-5 text-violet-400 shrink-0" />
              <div>
                <div className="font-semibold text-sm">{w.name}</div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {w.nodes?.length || 0} nodes &middot; {w.edges?.length || 0} edges
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => openTriggerModal(w.id)} className="text-emerald-400 hover:text-emerald-300 transition-colors" title="Trigger">
                <Play className="w-4 h-4" />
              </button>
              <Link href={`/workflows/${w.id}/edit`} className="text-zinc-400 hover:text-accent transition-colors" title="Edit">
                <Edit2 className="w-4 h-4" />
              </Link>
              <button onClick={() => remove(w.id)} className="text-zinc-400 hover:text-red-400 transition-colors" title="Delete">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {!loading && workflows.filter((w) => {
          if (!search) return true;
          const q = search.toLowerCase();
          return w.name.toLowerCase().includes(q) || (w.description || "").toLowerCase().includes(q) || String(w.nodes?.length || 0).includes(q);
        }).length === 0 && (
          <p className="text-zinc-500 text-sm">{search ? "No workflows match your search." : "No workflows yet."}</p>
        )}
      </div>

      {/* Trigger Modal */}
      {isTriggerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-bold flex items-center gap-2 text-violet-400">
                <Play className="w-4 h-4 fill-violet-400" /> Run Workflow
              </h3>
              <p className="text-xs text-zinc-400 mt-1">Configure inputs to execute the workflow.</p>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Input Prompt / Topic</label>
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  placeholder="e.g. OCR this receipt or research Quantum Computing"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent min-h-[90px]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Image Input (Optional)</label>
                {!selectedImage ? (
                  <label className="flex flex-col items-center justify-center border-2 border-dashed border-zinc-800 hover:border-zinc-700 bg-zinc-900/50 hover:bg-zinc-900 rounded-lg p-5 cursor-pointer transition-colors group">
                    <Plus className="w-6 h-6 text-zinc-500 group-hover:text-zinc-400 mb-1 animate-pulse" />
                    <span className="text-xs text-zinc-400 group-hover:text-zinc-300 font-medium">Click to select image</span>
                    <span className="text-[10px] text-zinc-500 mt-0.5">Supports PNG, JPG, WEBP</span>
                    <input type="file" accept="image/*" onChange={handleImageChange} className="hidden" />
                  </label>
                ) : (
                  <div className="relative border border-zinc-800 rounded-lg p-2 bg-zinc-900 flex items-center gap-3">
                    <img src={selectedImage} alt="Preview" className="w-14 h-14 rounded object-cover border border-zinc-800 bg-black shrink-0" />
                    <div className="min-w-0 flex-1">
                      <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">✓ Image Loaded</span>
                      <span className="text-[10px] text-zinc-500 block truncate mt-0.5">Inline base64 encoding active</span>
                    </div>
                    <button onClick={handleImageRemove} className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white px-2.5 py-1.5 rounded transition-colors shrink-0">
                      Remove
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setIsTriggerModalOpen(false)}
                disabled={triggering}
                className="text-zinc-400 hover:text-white text-sm px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleTriggerSubmit}
                disabled={triggering}
                className="bg-accent hover:bg-accent-hover text-white text-sm px-4 py-2 rounded transition-colors font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {triggering ? "Running..." : "Run Workflow"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
