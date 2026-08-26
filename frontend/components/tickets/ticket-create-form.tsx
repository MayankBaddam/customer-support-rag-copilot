"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { createTicket } from "@/lib/api-client";
import type { CustomerPlan, TicketCategory, TicketPriority } from "@/types/api";
import { categoryLabels, planLabels, priorityLabels, SelectField } from "@/components/tickets/ticket-ui";
import { validateTicketForm } from "@/lib/ticket-validation";

export function TicketCreateForm() {
  const { session } = useAuth(); const router = useRouter();
  const [form, setForm] = useState({ subject: "", customer_name: "", customer_email: "", customer_plan: "basic" as CustomerPlan, category: "billing" as TicketCategory, priority: "medium" as TicketPriority, content: "" });
  const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false);
  const update = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent) { event.preventDefault(); setError(null); const validationError = validateTicketForm({ subject: form.subject, customerName: form.customer_name, customerEmail: form.customer_email, initialMessage: form.content }); if (validationError) { setError(validationError); return; } if (!session) return; setLoading(true); try { const ticket = await createTicket(session.access_token, { subject: form.subject.trim(), customer_name: form.customer_name.trim(), customer_email: form.customer_email.trim(), customer_plan: form.customer_plan, category: form.category, priority: form.priority, first_message: { sender_type: "customer", sender_name: form.customer_name.trim(), content: form.content.trim() } }); router.replace(`/tickets/${ticket.id}`); } catch { setError("The ticket could not be created. Please try again."); } finally { setLoading(false); } }
  return <form className="ticket-form" onSubmit={submit}><div className="form-grid"><label>Subject<input value={form.subject} onChange={(event) => update("subject", event.target.value)} /></label><label>Customer name<input value={form.customer_name} onChange={(event) => update("customer_name", event.target.value)} /></label><label>Customer email<input type="email" value={form.customer_email} onChange={(event) => update("customer_email", event.target.value)} /></label><SelectField label="Plan" value={form.customer_plan} onChange={(value) => update("customer_plan", value)} options={planLabels} /><SelectField label="Category" value={form.category} onChange={(value) => update("category", value)} options={categoryLabels} /><SelectField label="Priority" value={form.priority} onChange={(value) => update("priority", value)} options={priorityLabels} /></div><label>Initial customer message<textarea value={form.content} onChange={(event) => update("content", event.target.value)} rows={6} /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? "Creating ticket..." : "Create ticket"}</button></form>;
}