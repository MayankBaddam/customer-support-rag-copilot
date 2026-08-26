"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { BackendStatus } from "@/components/layout/backend-status";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, router, user]);
  if (loading || !user) return <div className="auth-loading">Checking your session...</div>;
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