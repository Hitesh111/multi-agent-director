"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Workflow, Bot, GitMerge, ArrowRight, Sparkles } from "lucide-react";

const templates = [
  {
    name: "Research → Summarize → Review",
    description:
      "A complete research pipeline: an AI agent researches any topic, a second agent summarizes the findings, and a third agent reviews the output for quality.",
    nodes: ["Research Agent", "Summarizer Agent", "Reviewer Agent"],
    color: "text-violet-400",
    border: "border-violet-500/30",
  },
  {
    name: "Code Writer → Code Reviewer",
    description:
      "A software development pipeline: a coding agent writes a solution for a problem, and a senior code reviewer reviews it for optimizations and bugs.",
    nodes: ["Code Writer Agent", "Code Reviewer Agent"],
    color: "text-emerald-400",
    border: "border-emerald-500/30",
  },
  {
    name: "Image Analyzer",
    description:
      "An AI vision pipeline: an AI vision agent accepts an image URL, provides a structured visual description of the content, and extracts all readable text verbatim.",
    nodes: ["Image Analyzer Agent"],
    color: "text-amber-400",
    border: "border-amber-500/30",
  },
  {
    name: "Draft & Approve",
    description:
      "A human-in-the-loop pipeline: an AI drafts content, then pauses for human approval before producing the final output. Perfect for editorial workflows.",
    nodes: ["DraftWriter Agent", "Human Approval", "Output"],
    color: "text-rose-400",
    border: "border-rose-500/30",
  },
];

export default function TemplatesPage() {
  const router = useRouter();
  const [deploying, setDeploying] = useState<string | null>(null);
  const [result, setResult] = useState<{ templateName: string; message: string } | null>(null);

  async function deploy(templateName: string) {
    setDeploying(templateName);
    setResult(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/workflows/deploy_template/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ template_name: templateName }),
        },
      );
      const data = await res.json();
      setResult({ templateName, message: `Deployed! Workflow ID: ${data.workflow_id}` });
      setTimeout(() => router.push(`/workflows/${data.workflow_id}/edit`), 1500);
    } catch {
      setResult({ templateName, message: "Failed to deploy template. Is the backend running?" });
    }
    setDeploying(null);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Templates</h1>
        <p className="text-sm text-zinc-400 mt-1">Prebuilt workflow templates. Deploy with one click.</p>
      </div>

      <div className="grid gap-4">
        {templates.map((t) => (
          <div
            key={t.name}
            className={`bg-card border ${t.border} rounded-lg p-5 hover:border-accent/50 transition-colors`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <Sparkles className={`w-6 h-6 ${t.color}`} />
                <div>
                  <h2 className="font-semibold">{t.name}</h2>
                  <p className="text-sm text-zinc-400 mt-1">{t.description}</p>
                </div>
              </div>
            </div>

            {/* Pipeline visualization */}
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <Workflow className="w-4 h-4 text-zinc-500" />
              {t.nodes.map((node, i) => (
                <div key={node} className="flex items-center gap-2">
                  <span className="text-xs bg-zinc-800 border border-zinc-700 rounded px-2 py-1 flex items-center gap-1">
                    <Bot className="w-3 h-3 text-accent" />
                    {node}
                  </span>
                  {i < t.nodes.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-zinc-600" />
                  )}
                </div>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => deploy(t.name)}
                disabled={deploying !== null}
                className="bg-accent hover:bg-accent-hover text-white text-sm px-4 py-2 rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <GitMerge className="w-4 h-4" />
                {deploying === t.name ? "Deploying..." : "Deploy Template"}
              </button>
              {result && result.templateName === t.name && (
                <span className="text-sm text-emerald-400">{result.message}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
