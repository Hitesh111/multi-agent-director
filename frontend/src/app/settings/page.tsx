"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Bot, Info } from "lucide-react";

export default function SettingsPage() {
  const [botToken, setBotToken] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await api.getTelegramSettings();
        if (data.bot_token) {
          setBotToken(data.bot_token);
        }
      } catch (error) {
        console.error("Failed to load telegram settings:", error);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.updateTelegramSettings(botToken);
      setMessage({ type: "success", text: "Settings saved successfully." });
    } catch (error) {
      setMessage({ type: "error", text: "Failed to save settings. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-background p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">Settings</h1>
          <p className="text-sm text-zinc-400">Configure global application settings and integrations.</p>
        </div>

        <div className="bg-sidebar border border-border rounded-lg overflow-hidden">
          <div className="p-6 border-b border-border">
            <div className="flex items-center gap-2 mb-2">
              <Bot className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-semibold">Telegram Bot Configuration</h2>
            </div>
            <p className="text-sm text-zinc-400">
              Connect your own Telegram bot to interact with agents directly from Telegram.
            </p>
          </div>
          
          <div className="p-6 space-y-6">
            <div className="bg-accent/10 border border-accent/20 rounded p-4 flex gap-3">
              <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />
              <div className="text-sm text-accent/90 space-y-2">
                <p className="font-semibold text-accent">How to connect your bot:</p>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Open Telegram and search for <strong>@BotFather</strong>.</li>
                  <li>Send the <code>/newbot</code> command and follow the prompts.</li>
                  <li>BotFather will give you an HTTP API Token.</li>
                  <li>Paste that token into the field below and save.</li>
                </ol>
              </div>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
              {message && (
                <div className={`p-3 rounded text-sm ${message.type === "success" ? "bg-green-900/30 border border-green-700 text-green-300" : "bg-red-900/30 border border-red-700 text-red-300"}`}>
                  {message.text}
                </div>
              )}

              <div>
                <label htmlFor="bot-token" className="block text-sm font-medium text-zinc-300 mb-2">
                  Telegram Bot API Token
                </label>
                <input
                  id="bot-token"
                  type="password"
                  placeholder="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  value={botToken}
                  onChange={(e) => setBotToken(e.target.value)}
                  disabled={loading || saving}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent disabled:opacity-50"
                />
                <p className="text-xs text-zinc-500 mt-2">
                  Keep this token secure. Do not share it publicly.
                </p>
              </div>

              <div className="pt-4 border-t border-border flex justify-end">
                <button
                  type="submit"
                  disabled={loading || saving}
                  className="bg-accent text-white rounded px-4 py-2 text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {saving ? "Saving..." : "Save Configuration"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
