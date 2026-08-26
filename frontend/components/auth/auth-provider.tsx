"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useState } from "react";
import type { AuthState } from "@/types/auth";
import { getSession, signOut, subscribeToAuthChanges } from "@/lib/auth-client";

const AuthContext = createContext<AuthState & { signOut: () => Promise<void> } | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, session: null, loading: true });
  useEffect(() => {
    let active = true;
    getSession().then(({ data }) => {
      if (active) setState({ user: data.session?.user ?? null, session: data.session, loading: false });
    });
    const { data: listener } = subscribeToAuthChanges((_event, session) => {
      setState({ user: session?.user ?? null, session, loading: false });
    });
    return () => { active = false; listener.subscription.unsubscribe(); };
  }, []);
  return <AuthContext.Provider value={{ ...state, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}