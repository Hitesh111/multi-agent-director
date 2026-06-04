"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, getAuthHeaders, ApiError } from "@/lib/api";
import { Terminal } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fn = isRegister ? api.register : api.login;
      const res = await fn(username, password);
      localStorage.setItem("auth_token", res.token);
      router.push("/");
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.apiMessage
          : err instanceof Error
            ? err.message
            : "Authentication failed"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm mx-auto p-6">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Terminal className="w-6 h-6 text-accent" />
          <span className="font-bold text-lg">YunoAI</span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <h1 className="text-xl font-bold text-center">
            {isRegister ? "Create Account" : "Sign In"}
          </h1>
          {error && (
            <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded p-3">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent text-white rounded py-2 text-sm font-semibold hover:bg-accent/90 disabled:opacity-50"
          >
            {loading ? "Loading..." : isRegister ? "Create Account" : "Sign In"}
          </button>
          <p className="text-center text-sm text-zinc-500">
            {isRegister ? (
              <>Already have an account?{" "}<button type="button" onClick={() => setIsRegister(false)} className="text-accent hover:underline">Sign in</button></>
            ) : (
              <>No account?{" "}<button type="button" onClick={() => setIsRegister(true)} className="text-accent hover:underline">Create one</button></>
            )}
          </p>
        </form>
      </div>
    </div>
  );
}
