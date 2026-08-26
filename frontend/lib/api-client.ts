import type { CustomerPlan, HealthResponse, Message, MessageCreate, TicketCategory, TicketDetail, TicketListResponse, TicketPriority, TicketStatus } from "@/types/api";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiClientError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiClientError";
  }
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}/health`, { signal, cache: "no-store" });
  } catch {
    throw new ApiClientError("The backend could not be reached.");
  }
  if (!response.ok) {
    throw new ApiClientError("The backend returned an unexpected response.", response.status);
  }
  return (await response.json()) as HealthResponse;
}

export async function getCurrentProfile(accessToken: string): Promise<import("@/types/api").ProfileResponse> {
  const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!response.ok) throw new ApiClientError("The authenticated profile could not be loaded.", response.status);
  return (await response.json()) as import("@/types/api").ProfileResponse;
}

async function request<T>(path: string, token: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { ...options, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...options?.headers }, cache: "no-store" });
  if (!response.ok) throw new ApiClientError("The ticket request could not be completed.", response.status);
  return (await response.json()) as T;
}

export interface TicketFilters { page: number; pageSize: number; search?: string; status?: TicketStatus; priority?: TicketPriority; category?: TicketCategory; plan?: CustomerPlan; }
export function getTickets(token: string, filters: TicketFilters) {
  const params = new URLSearchParams({ page: String(filters.page), page_size: String(filters.pageSize) });
  if (filters.search) params.set("search", filters.search);
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.category) params.set("category", filters.category);
  if (filters.plan) params.set("plan", filters.plan);
  return request<TicketListResponse>(`/api/v1/tickets?${params}`, token);
}

export function getTicket(token: string, id: string) { return request<TicketDetail>(`/api/v1/tickets/${id}`, token); }
export function updateTicket(token: string, id: string, data: Partial<Pick<TicketDetail, "subject" | "status" | "priority" | "category" | "customer_plan" | "assigned_to">>) { return request<TicketDetail>(`/api/v1/tickets/${id}`, token, { method: "PATCH", body: JSON.stringify(data) }); }
export function addTicketMessage(token: string, id: string, data: MessageCreate) { return request<Message>(`/api/v1/tickets/${id}/messages`, token, { method: "POST", body: JSON.stringify(data) }); }
export function createTicket(token: string, data: { subject: string; customer_name: string; customer_email: string; customer_plan: CustomerPlan; category: TicketCategory; priority: TicketPriority; first_message?: MessageCreate }) { return request<TicketDetail>("/api/v1/tickets", token, { method: "POST", body: JSON.stringify(data) }); }