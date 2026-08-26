"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { getTickets, type TicketFilters } from "@/lib/api-client";
import type { TicketCategory, TicketPriority, TicketStatus } from "@/types/api";
import { categoryLabels, PriorityBadge, SelectField, StatusBadge, priorityLabels, statusLabels } from "@/components/tickets/ticket-ui";

export function TicketList() {
  const { session } = useAuth(); const router = useRouter(); const pathname = usePathname(); const params = useSearchParams();
  const [search, setSearch] = useState(params.get("search") ?? ""); const [debouncedSearch, setDebouncedSearch] = useState(search);
  const page = Number(params.get("page") ?? "1"); const pageSize = 8;
  const status = params.get("status") as TicketStatus | null; const priority = params.get("priority") as TicketPriority | null; const category = params.get("category") as TicketCategory | null;
  useEffect(() => { const timer = window.setTimeout(() => setDebouncedSearch(search), 350); return () => window.clearTimeout(timer); }, [search]);
  useEffect(() => {
    const next = new URLSearchParams(params.toString());
    if (debouncedSearch) next.set("search", debouncedSearch);
    else next.delete("search");
    if (params.get("search") !== (debouncedSearch || null)) {
      next.set("page", "1");
      router.replace(`${pathname}?${next}`);
    }
  }, [debouncedSearch, pathname, params, router]);
  const filters: TicketFilters = { page, pageSize, search: debouncedSearch, status: status ?? undefined, priority: priority ?? undefined, category: category ?? undefined };
  const query = useQuery({ queryKey: ["tickets", filters], queryFn: () => getTickets(session!.access_token, filters), enabled: Boolean(session) });
  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    next.set("page", "1");
    router.push(`${pathname}?${next}`);
  };
  if (query.isLoading) return <TicketListSkeleton />;
  if (query.isError) return <div className="ticket-state"><h2>Tickets could not load</h2><p>Check the backend connection and try again.</p><button className="secondary-button" onClick={() => query.refetch()}>Retry</button></div>;
  const data = query.data!; const pageCount = Math.max(1, Math.ceil(data.total / data.page_size));
  return <div className="ticket-workspace"><div className="ticket-toolbar"><input className="search-input" placeholder="Search tickets, customers, or email" value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search tickets" /><SelectField label="Status" value={status ?? ""} onChange={(value) => updateFilter("status", value)} options={statusLabels} /><SelectField label="Priority" value={priority ?? ""} onChange={(value) => updateFilter("priority", value)} options={priorityLabels} /><SelectField label="Category" value={category ?? ""} onChange={(value) => updateFilter("category", value)} options={categoryLabels} /><Link className="primary-button" href="/tickets/new">New ticket</Link></div>{data.items.length === 0 ? <div className="ticket-state"><h2>No tickets found</h2><p>Try broadening your search or removing a filter.</p></div> : <><div className="ticket-table-wrap"><table className="ticket-table"><thead><tr><th>Ticket</th><th>Customer</th><th>Category</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead><tbody>{data.items.map((ticket) => <tr key={ticket.id}><td><Link className="ticket-link" href={`/tickets/${ticket.id}`}><strong>{ticket.ticket_number}</strong><span>{ticket.subject}</span></Link></td><td><strong>{ticket.customer_name}</strong><span>{ticket.customer_plan}</span></td><td>{categoryLabels[ticket.category]}</td><td><PriorityBadge value={ticket.priority} /></td><td><StatusBadge value={ticket.status} /></td><td>{new Date(ticket.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div><div className="ticket-cards">{data.items.map((ticket) => <Link className="ticket-card" href={`/tickets/${ticket.id}`} key={ticket.id}><div><strong>{ticket.ticket_number}</strong><StatusBadge value={ticket.status} /></div><h3>{ticket.subject}</h3><p>{ticket.customer_name} · {categoryLabels[ticket.category]}</p><PriorityBadge value={ticket.priority} /></Link>)}</div><div className="pagination"><button className="secondary-button" disabled={page <= 1} onClick={() => updateFilter("page", String(page - 1))}>Previous</button><span>Page {page} of {pageCount}</span><button className="secondary-button" disabled={page >= pageCount} onClick={() => updateFilter("page", String(page + 1))}>Next</button></div></>}</div>;
}

function TicketListSkeleton() { return <div className="ticket-skeleton" aria-label="Loading tickets">{Array.from({ length: 6 }, (_, index) => <div key={index} />)}</div>; }