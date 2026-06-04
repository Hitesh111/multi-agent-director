import type { Metadata } from "next";
import "./globals.css";
import AuthGuard from "@/components/auth-guard";

export const metadata: Metadata = {
  title: "YunoAI - Agent Orchestrator",
  description: "AI Agent Orchestration Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
