import type { ApiError, CustomerPlan, DocumentChunkListResponse, DocumentFileType, DocumentListResponse, DocumentStatus, GroundedAnswerResponse, HealthResponse, KnowledgeDocument, Message, MessageCreate, SemanticSearchRequest, SemanticSearchResponse, TicketCategory, TicketDetail, TicketListResponse, TicketPriority, TicketStatus } from "@/types/api";

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
  return request<import("@/types/api").ProfileResponse>("/api/v1/auth/me", accessToken);
}

async function request<T>(path: string, token: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const headers = new Headers(options?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (options?.body && !isFormData) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new ApiClientError("The backend could not be reached.");
  }
  if (!response.ok) {
    let message = "The request could not be completed.";
    try {
      const payload = (await response.json()) as Partial<ApiError>;
      if (payload.error?.message) message = payload.error.message;
    } catch {
      // Keep the safe generic message when the backend response is not JSON.
    }
    throw new ApiClientError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
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

export interface DocumentFilters { page: number; pageSize: number; search?: string; status?: DocumentStatus; fileType?: DocumentFileType; }
export function getDocuments(token: string, filters: DocumentFilters) {
  const params = new URLSearchParams({ page: String(filters.page), page_size: String(filters.pageSize) });
  if (filters.search) params.set("search", filters.search);
  if (filters.status) params.set("status", filters.status);
  if (filters.fileType) params.set("file_type", filters.fileType);
  return request<DocumentListResponse>(`/api/v1/documents?${params}`, token);
}
export function getDocument(token: string, id: string) { return request<KnowledgeDocument>(`/api/v1/documents/${id}`, token); }
export function getDocumentChunks(token: string, id: string, page: number, pageSize = 10) { return request<DocumentChunkListResponse>(`/api/v1/documents/${id}/chunks?page=${page}&page_size=${pageSize}`, token); }
export function uploadDocument(token: string, title: string, file: File) { const body = new FormData(); body.set("title", title); body.set("file", file); return request<KnowledgeDocument>("/api/v1/documents", token, { method: "POST", body }); }
export function processDocument(token: string, id: string) { return request<KnowledgeDocument>(`/api/v1/documents/${id}/process`, token, { method: "POST" }); }
export function reprocessDocument(token: string, id: string) { return request<KnowledgeDocument>(`/api/v1/documents/${id}/reprocess`, token, { method: "POST" }); }
export function deleteDocument(token: string, id: string) { return request<void>(`/api/v1/documents/${id}`, token, { method: "DELETE" }); }

export async function searchKnowledgeChunks(token: string, payload: SemanticSearchRequest): Promise<SemanticSearchResponse> {
  const startedAt = performance.now();
  const response = await request<SemanticSearchResponse>("/api/v1/copilot/search", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const documentIds = [...new Set(response.results.map((result) => result.document_id))];
  const documents = await Promise.all(documentIds.map((documentId) => getDocument(token, documentId)));
  const filenames = new Map(documents.map((document) => [document.id, document.original_filename]));
  return {
    ...response,
    retrieval_latency_ms: response.retrieval_latency_ms ?? Math.max(0, performance.now() - startedAt),
    results: response.results.map((result) => ({
      ...result,
      original_filename: filenames.get(result.document_id),
    })),
  };
}

export function generateGroundedAnswer(token: string, payload: SemanticSearchRequest) {
  return request<GroundedAnswerResponse>("/api/v1/copilot/answer", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
