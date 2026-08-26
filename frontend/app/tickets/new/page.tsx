import { AppShell } from "@/components/layout/app-shell";
import { PageIntro } from "@/components/layout/page-intro";
import { TicketCreateForm } from "@/components/tickets/ticket-create-form";

export default function NewTicketPage() { return <AppShell><PageIntro eyebrow="New request" title="Create a ticket" description="Capture the customer context so the support team can move quickly." /><TicketCreateForm /></AppShell>; }