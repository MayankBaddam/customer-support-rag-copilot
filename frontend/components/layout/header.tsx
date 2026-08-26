import type { ReactNode } from "react";

export function Header({ children }: { children: ReactNode }) {
  return <header className="top-header"><span className="header-context">Support operations / workspace</span><div className="header-actions">{children}<span className="avatar" aria-label="Current user">MS</span></div></header>;
}