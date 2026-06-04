const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  apiMessage: string;
  constructor(message: string, status: number, body?: string) {
    super(message);
    this.status = status;
    try {
      const parsed = JSON.parse(body || "{}");
      this.apiMessage = parsed.error || parsed.detail || parsed.message || message;
    } catch {
      this.apiMessage = message;
    }
  }
}

const inflight = new Map<string, Promise<unknown>>();

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem("auth_token");
}

function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Token ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  const url = `${API_BASE}${path}`;

  const cacheKey = `${options?.method || "GET"}:${url}`;
  if (inflight.has(cacheKey) && (!options?.method || options.method === "GET")) {
    return inflight.get(cacheKey) as Promise<T>;
  }

  const promise = (async () => {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...options?.headers },
      signal: options?.signal,
      ...options,
    });
    if (res.status === 401 || res.status === 403) {
      clearToken();
    }
    if (!res.ok) {
      const body = await res.text();
      throw new ApiError(`API ${res.status}: ${body}`, res.status, body);
    }
    return res.json() as Promise<T>;
  })();

  if (!options?.method || options.method === "GET") {
    inflight.set(cacheKey, promise);
    promise.finally(() => inflight.delete(cacheKey));
  }

  return promise;
}

import type { Agent, Workflow, Execution, Message } from "./types";

export const api = {
  // Agents
  listAgents: (params?: string, signal?: AbortSignal) =>
    request<{ results: Agent[] }>(`/agents/${params || ""}`, { signal }),
  getAgent: (id: number, signal?: AbortSignal) =>
    request<Agent>(`/agents/${id}/`, { signal }),
  createAgent: (data: Partial<Agent>) =>
    request<Agent>("/agents/", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: number, data: Partial<Agent>) =>
    request<Agent>(`/agents/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteAgent: (id: number) =>
    request<void>(`/agents/${id}/`, { method: "DELETE" }),

  // Workflows
  listWorkflows: (params?: string, signal?: AbortSignal) =>
    request<{ results: Workflow[] }>(`/workflows/${params || ""}`, { signal }),
  getWorkflow: (id: number, signal?: AbortSignal) =>
    request<Workflow>(`/workflows/${id}/`, { signal }),
  createWorkflow: (data: Partial<Workflow>) =>
    request<Workflow>("/workflows/", { method: "POST", body: JSON.stringify(data) }),
  updateWorkflow: (id: number, data: Partial<Workflow>) =>
    request<Workflow>(`/workflows/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteWorkflow: (id: number) =>
    request<void>(`/workflows/${id}/`, { method: "DELETE" }),
  triggerWorkflow: (id: number, input: Record<string, unknown>) =>
    request<Execution>(`/workflows/${id}/trigger/`, { method: "POST", body: JSON.stringify({ input_data: input }) }),

  // Executions
  listExecutions: (params?: string, signal?: AbortSignal) =>
    request<{ results: Execution[] }>(`/executions/${params || ""}`, { signal }),
  getExecution: (id: number, signal?: AbortSignal) =>
    request<Execution>(`/executions/${id}/`, { signal }),
  cancelExecution: (id: number) =>
    request<Execution>(`/executions/${id}/cancel/`, { method: "POST" }),
  approveExecution: (id: number, approved: boolean, feedback?: string) =>
    request<Execution>(`/executions/${id}/approve/`, {
      method: "POST",
      body: JSON.stringify({ approved, feedback: feedback || "" }),
    }),

  // Messages
  listMessages: (params?: string, signal?: AbortSignal) =>
    request<{ results: Message[] }>(`/messages/${params || ""}`, { signal }),

  // Telegram Settings
  getTelegramSettings: (signal?: AbortSignal) =>
    request<{ bot_token: string; updated_at: string }>("/telegram/settings/", { signal }),
  updateTelegramSettings: (bot_token: string) =>
    request<{ bot_token: string; updated_at: string }>("/telegram/settings/", {
      method: "PATCH",
      body: JSON.stringify({ bot_token }),
    }),

  // Dashboard stats
  getStats: (signal?: AbortSignal) =>
    request<{ agents: number; workflows: number; executions: number; execution_statuses: Record<string, number> }>("/stats/", { signal }),

  // Auth
  login: (username: string, password: string) =>
    request<{ token: string; user_id: number; username: string }>("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, password: string) =>
    request<{ token: string; user_id: number; username: string }>("/auth/register/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<{ detail: string }>("/auth/logout/", { method: "POST" })
      .then((res) => { clearToken(); return res; })
      .catch((e) => { clearToken(); throw e; }),
};
