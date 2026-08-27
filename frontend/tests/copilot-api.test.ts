import { afterEach, describe, expect, it, vi } from "vitest";
import { generateGroundedAnswer } from "@/lib/api-client";

describe("Copilot answer API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts the question with the authenticated API client", async () => {
    const response = { answer: "Grounded answer", citations: [], retrieved_chunks: 0 };
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(new Response(JSON.stringify(response), { status: 200 }));

    await expect(generateGroundedAnswer("access-token", { query: "Recovery policy", top_k: 4 })).resolves.toEqual(response);

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/copilot/answer");
    expect(options?.method).toBe("POST");
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer access-token");
    expect(options?.body).toBe(JSON.stringify({ query: "Recovery policy", top_k: 4 }));
  });
});
