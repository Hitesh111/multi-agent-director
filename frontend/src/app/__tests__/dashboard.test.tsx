import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "../page";

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
}));

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      results: [],
    }),
  });
});

describe("Dashboard Page", () => {
  it("renders the dashboard title", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("renders summary cards", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Agents")).toBeInTheDocument();
      expect(screen.getByText("Workflows")).toBeInTheDocument();
      expect(screen.getByText("Executions")).toBeInTheDocument();
    });
  });

  it("renders Recent Executions section", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Recent Executions")).toBeInTheDocument();
    });
  });
});
