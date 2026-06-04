"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bot, Workflow, Play, LayoutDashboard, Terminal, FileJson, LogOut, Settings as SettingsIcon } from "lucide-react";
import { api } from "@/lib/api";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/templates", label: "Templates", icon: FileJson },
  { href: "/executions", label: "Executions", icon: Play },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Clear token locally even if backend call fails
    }
    router.replace("/login");
  };

  return (
    <aside className="w-56 bg-sidebar border-r border-border flex flex-col h-screen shrink-0">
      <div className="p-4 border-b border-border flex items-center gap-2">
        <Terminal className="w-5 h-5 text-accent" />
        <span className="font-bold text-sm">YunoAI</span>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {links.map((l) => {
          const active = path === l.href || path.startsWith(`${l.href}/`);
          const Icon = l.icon;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
                active
                  ? "bg-accent/10 text-accent"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              {l.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-2 border-t border-border">
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors w-full text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
