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

export type DocumentStatus = "pending" | "processing" | "completed" | "failed" | "archived";
export type DocumentFileType = "pdf" | "markdown" | "text";

export interface KnowledgeDocument {
  id: string;
  title: string;
  original_filename: string;
  storage_bucket: string;
  file_type: DocumentFileType;
  mime_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  status: DocumentStatus;
  version: number;
  chunk_count: number;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

export interface DocumentListResponse {
  items: KnowledgeDocument[];
  page: number;
  page_size: number;
  total: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  section_title: string | null;
  page_number: number | null;
  token_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DocumentChunkListResponse {
  items: DocumentChunk[];
  page: number;
  page_size: number;
  total: number;
}

export interface SemanticSearchRequest {
  query: string;
  top_k: number;
}

export interface SemanticSearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  original_filename?: string;
  section_title: string | null;
  page_number: number | null;
  content: string;
  similarity_score: number;
}

export interface SemanticSearchResponse {
  request_id: string;
  query: string;
  results: SemanticSearchResult[];
  result_count: number;
  retrieval_latency_ms?: number;
  embedding_model: string;
  evidence_status: "found" | "no_evidence";
}

export interface GroundedAnswerCitation {
  chunk_id: string;
  document_title: string;
  original_filename: string;
  section_title: string | null;
  page_number: number | null;
  similarity_score: number;
}

export interface GroundedAnswerResponse {
  answer: string;
  citations: GroundedAnswerCitation[];
  retrieved_chunks: number;
}
