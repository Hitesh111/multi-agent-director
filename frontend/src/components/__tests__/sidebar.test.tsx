import { act } from "@testing-library/react";
import { render, screen, fireEvent } from "@testing-library/react";
import Sidebar from "../sidebar";
import { usePathname, useRouter } from "next/navigation";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockReplace = vi.fn();
const mockLogout = vi.hoisted(() => vi.fn().mockResolvedValue({ detail: "logged out" }));

vi.mock("@/lib/api", () => ({
  api: {
    logout: mockLogout,
  },
}));

describe("Sidebar Navigation Component", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockClear();
    vi.mocked(useRouter).mockReturnValue({ replace: mockReplace } as unknown as ReturnType<typeof useRouter>);
    mockReplace.mockClear();
    mockLogout.mockClear();
    mockLogout.mockResolvedValue({ detail: "logged out" });
  });

  it("renders all navigation links", () => {
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Sidebar />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Workflows")).toBeInTheDocument();
    expect(screen.getByText("Templates")).toBeInTheDocument();
    expect(screen.getByText("Executions")).toBeInTheDocument();
  });

  it("renders logout button", () => {
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Sidebar />);
    expect(screen.getByText("Logout")).toBeInTheDocument();
  });

  it("highlights the active link correctly", () => {
    vi.mocked(usePathname).mockReturnValue("/agents");
    render(<Sidebar />);

    const dashboardLink = screen.getByText("Dashboard").closest("a");
    const agentsLink = screen.getByText("Agents").closest("a");

    expect(agentsLink).toHaveClass("text-accent");

    expect(dashboardLink).not.toHaveClass("text-accent");
    expect(dashboardLink).toHaveClass("text-zinc-400");
  });


  it("calls logout and redirects on click", async () => {
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Sidebar />);

    await act(async () => {
      fireEvent.click(screen.getByText("Logout"));
    });

    expect(mockLogout).toHaveBeenCalledOnce();
    await vi.waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });
});
