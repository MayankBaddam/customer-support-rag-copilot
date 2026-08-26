import type { ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";

export function Header({ children }: { children: ReactNode }) {
  const { signOut } = useAuth();
  const router = useRouter();
  async function logout() { await signOut(); router.replace("/login"); }
  return <header className="top-header"><span className="header-context">Support operations / workspace</span><div className="header-actions">{children}<button className="logout-button" onClick={logout}>Sign out</button><span className="avatar" aria-label="Current user">MS</span></div></header>;
}