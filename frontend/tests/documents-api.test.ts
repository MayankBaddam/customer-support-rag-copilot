import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, deleteDocument, getDocuments, processDocument, uploadDocument } from "@/lib/api-client";

describe("document API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the access token and serializes list filters", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, page: 2, page_size: 10 }), { status: 200 }));
    await getDocuments("access-token", { page: 2, pageSize: 10, search: "guide", status: "completed", fileType: "pdf" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("page=2&page_size=10&search=guide&status=completed&file_type=pdf");
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer access-token");
  });

  it("uploads multipart form data without setting its Content-Type boundary", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "doc-1" }), { status: 201 }));
    const file = new File(["hello"], "guide.txt", { type: "text/plain" });
    await uploadDocument("token", "Guide", file);
    const [, options] = fetchMock.mock.calls[0]; const headers = new Headers(options?.headers);
    expect(options?.body).toBeInstanceOf(FormData);
    expect(headers.get("Content-Type")).toBeNull();
    expect((options?.body as FormData).get("title")).toBe("Guide");
  });

  it("surfaces safe backend upload and processing errors", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { code: "FILE_TOO_LARGE", message: "The file is too large." } }), { status: 400 }));
    await expect(uploadDocument("token", "Guide", new File(["x"], "guide.txt"))).rejects.toEqual(expect.objectContaining({ message: "The file is too large.", status: 400 }));
    await expect(processDocument("token", "doc-1")).rejects.toBeInstanceOf(ApiClientError);
  });

  it("handles a successful empty delete response", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    await expect(deleteDocument("token", "doc-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/v1/documents/doc-1"), expect.objectContaining({ method: "DELETE" }));
  });
});
