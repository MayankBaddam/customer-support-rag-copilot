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