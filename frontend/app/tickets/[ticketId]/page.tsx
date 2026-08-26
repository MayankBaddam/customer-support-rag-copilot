import { AppShell } from "@/components/layout/app-shell";
import { TicketDetail } from "@/components/tickets/ticket-detail";

export default async function TicketDetailPage({ params }: { params: Promise<{ ticketId: string }> }) { const { ticketId } = await params; return <AppShell><TicketDetail ticketId={ticketId} /></AppShell>; }