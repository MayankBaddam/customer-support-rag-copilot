"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { signIn, signUp } from "@/lib/auth-client";
import { validateAuthForm } from "@/lib/auth-validation";

export function AuthForm({ registration = false }: { registration?: boolean }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setMessage(null);
    const validationError = validateAuthForm({ email, password, fullName }, registration);
    if (validationError) { setError(validationError); return; }
    setLoading(true);
    const result = registration
      ? await signUp(email, password, fullName.trim())
      : await signIn(email, password);
    setLoading(false);
    if (result.error) { setError(registration ? result.error.message : "Invalid email or password."); return; }
    if (registration && !result.data.session) { setMessage("Check your email to confirm your account, then sign in."); return; }
    router.replace("/");
  }
  return <div className="auth-card">
    <div className="auth-heading"><span className="brand-mark">CD</span><p className="eyebrow">CloudDesk support</p><h1>{registration ? "Create your workspace access" : "Welcome back"}</h1><p>{registration ? "Set up an account for the internal support workspace." : "Sign in to continue to your support workspace."}</p></div>
    <form onSubmit={submit} className="auth-form" noValidate>
      {registration && <label>Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} autoComplete="name" /></label>}
      <label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
      <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={registration ? "new-password" : "current-password"} /></label>
      {error && <p className="auth-error" role="alert">{error}</p>}
      {message && <p className="auth-message" role="status">{message}</p>}
      <button className="auth-submit" disabled={loading}>{loading ? "Working..." : registration ? "Create account" : "Sign in"}</button>
    </form>
    <p className="auth-switch">{registration ? "Already have access?" : "Need an account?"} <Link href={registration ? "/login" : "/register"}>{registration ? "Sign in" : "Register"}</Link></p>
  </div>;
}