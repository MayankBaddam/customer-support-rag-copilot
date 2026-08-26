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