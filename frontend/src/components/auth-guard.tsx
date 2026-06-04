"use client";

import { useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import Sidebar from "@/components/sidebar";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = typeof localStorage !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (!token && !PUBLIC_PATHS.includes(pathname)) {
      router.replace("/login");
    } else {
      setChecked(true);
    }
  }, [pathname, router]);

  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (!checked && !isPublic) {
    return null;
  }

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <div className="h-full flex">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
