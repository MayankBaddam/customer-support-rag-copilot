import { AppShell } from "@/components/layout/app-shell";
import { PageIntro } from "@/components/layout/page-intro";
import { TicketList } from "@/components/tickets/ticket-list";

export default function TicketsPage() {
  return <AppShell><PageIntro eyebrow="Ticket queue" title="Tickets" description="A focused view for the conversations that need your team&apos;s attention." /><TicketList /></AppShell>;
}