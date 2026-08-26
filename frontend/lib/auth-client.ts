import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

export function getSession() {
  return supabase?.auth.getSession() ?? Promise.resolve({ data: { session: null }, error: null });
}

export function subscribeToAuthChanges(callback: (event: AuthChangeEvent, session: Session | null) => void) {
  return supabase?.auth.onAuthStateChange(callback) ?? { data: { subscription: { unsubscribe: () => undefined } } };
}

export async function signOut(): Promise<void> {
  await (supabase?.auth.signOut() ?? Promise.resolve({ error: null }));
}

export function signIn(email: string, password: string) {
  return supabase?.auth.signInWithPassword({ email, password }) ?? Promise.resolve({ data: { user: null, session: null }, error: new Error("Authentication is not configured.") });
}

export function signUp(email: string, password: string, fullName: string) {
  return supabase?.auth.signUp({ email, password, options: { data: { full_name: fullName } } }) ?? Promise.resolve({ data: { user: null, session: null }, error: new Error("Authentication is not configured.") });
}