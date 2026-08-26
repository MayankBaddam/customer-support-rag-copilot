"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { BackendStatus } from "@/components/layout/backend-status";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="app-shell">
      <Sidebar pathname={pathname} />
      <div className="main-area">
        <Header><BackendStatus /></Header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}