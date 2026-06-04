import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../api";

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("API Client", () => {
  it("listAgents returns parsed results", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [{ id: 1, name: "TestAgent", provider: "deepseek" }] }),
    });
    const res = await api.listAgents();
    expect(res.results).toHaveLength(1);
    expect(res.results[0].name).toBe("TestAgent");
  });

  it("getAgent returns single agent", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, name: "AgentOne", provider: "grok" }),
    });
    const res = await api.getAgent(1);
    expect(res.name).toBe("AgentOne");
    expect(res.provider).toBe("grok");
  });

  it("createAgent sends POST and returns agent", async () => {
    const newAgent = { name: "NewAgent", provider: "deepseek", model: "deepseek-chat" };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 2, ...newAgent }),
    });
    const res = await api.createAgent(newAgent);
    expect(res.id).toBe(2);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/agents/"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("NewAgent"),
      }),
    );
  });

  it("updateAgent sends PATCH", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, name: "Updated", provider: "deepseek" }),
    });
    const res = await api.updateAgent(1, { name: "Updated" });
    expect(res.name).toBe("Updated");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/agents/1/"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("deleteAgent sends DELETE", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => {} });
    await api.deleteAgent(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/agents/1/"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("listWorkflows returns workflows", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [{ id: 1, name: "TestWF", nodes: [], edges: [] }] }),
    });
    const res = await api.listWorkflows();
    expect(res.results).toHaveLength(1);
  });

  it("triggerWorkflow sends POST and returns execution", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 42, status: "running", workflow: 1 }),
    });
    const res = await api.triggerWorkflow(1, { text: "hello" });
    expect(res.id).toBe(42);
    expect(res.status).toBe("running");
  });

  it("cancelExecution sends POST", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, status: "cancelled" }),
    });
    const res = await api.cancelExecution(1);
    expect(res.status).toBe("cancelled");
  });

  it("listMessages returns messages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [{ id: 1, role: "assistant", content: "hi" }] }),
    });
    const res = await api.listMessages("?execution=1");
    expect(res.results).toHaveLength(1);
  });

  it("throws ApiError on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: async () => "Not found",
    });
    await expect(api.getAgent(999)).rejects.toThrow("API 404");
  });

  it("ApiError parses JSON error body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => '{"error":"invalid credentials"}',
    });
    try {
      await api.getAgent(999);
    } catch (e) {
      const err = e as import("../api").ApiError;
      expect(err.apiMessage).toBe("invalid credentials");
      expect(err.status).toBe(401);
    }
  });

  it("logout calls POST /auth/logout/ and clears token", async () => {
    localStorage.setItem("auth_token", "test-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ detail: "logged out" }),
    });
    const res = await api.logout();
    expect(res.detail).toBe("logged out");
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/logout/"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
