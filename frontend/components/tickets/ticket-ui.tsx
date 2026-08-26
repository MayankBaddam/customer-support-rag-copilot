import type { CustomerPlan, TicketCategory, TicketPriority, TicketStatus } from "@/types/api";

export const statusLabels: Record<TicketStatus, string> = { open: "Open", in_progress: "In progress", waiting: "Waiting", resolved: "Resolved" };
export const priorityLabels: Record<TicketPriority, string> = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
export const categoryLabels: Record<TicketCategory, string> = { billing: "Billing", account_access: "Account access", subscription: "Subscription", integration: "Integration", security: "Security", technical: "Technical" };
export const planLabels: Record<CustomerPlan, string> = { free: "Free", basic: "Basic", pro: "Pro" };

export function StatusBadge({ value }: { value: TicketStatus }) { return <span className={`ticket-badge badge-${value}`}>{statusLabels[value]}</span>; }
export function PriorityBadge({ value }: { value: TicketPriority }) { return <span className={`ticket-badge priority-${value}`}>{priorityLabels[value]}</span>; }
export function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: Record<string, string> }) { return <label className="filter-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">All</option>{Object.entries(options).map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>; }