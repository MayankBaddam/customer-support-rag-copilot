export type BackendStatus = "loading" | "online" | "offline";

export interface HealthResponse {
  status: "ok";
  service: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}

export interface ProfileResponse {
  id: string;
  full_name: string;
  role: "agent" | "admin";
}

export type TicketStatus = "open" | "in_progress" | "waiting" | "resolved";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketCategory = "billing" | "account_access" | "subscription" | "integration" | "security" | "technical";
export type CustomerPlan = "free" | "basic" | "pro";
export type SenderType = "customer" | "agent" | "system";
export interface MessageCreate { sender_type: SenderType; sender_name: string; content: string; }

export interface Message {
  id: string;
  sender_type: SenderType;
  sender_name: string;
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  created_at: string;
  messages: Message[];
}

export interface Ticket {
  id: string;
  ticket_number: string;
  subject: string;
  customer_name: string;
  customer_email: string;
  customer_plan: CustomerPlan;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  assigned_to: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends Ticket { conversations: Conversation[]; }
export interface TicketListResponse { total: number; page: number; page_size: number; items: Ticket[]; }