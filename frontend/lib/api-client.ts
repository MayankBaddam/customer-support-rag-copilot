import type { HealthResponse } from "@/types/api";

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