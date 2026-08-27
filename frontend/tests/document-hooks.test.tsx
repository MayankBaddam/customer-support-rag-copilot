import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ upload: vi.fn(), process: vi.fn(), reprocess: vi.fn(), remove: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ useAuth: () => ({ session: { access_token: "access-token" } }) }));
vi.mock("@/lib/api-client", () => ({
  uploadDocument: mocks.upload, processDocument: mocks.process, reprocessDocument: mocks.reprocess, deleteDocument: mocks.remove,
  getDocuments: vi.fn(), getDocument: vi.fn(), getDocumentChunks: vi.fn(),
}));
import { useDeleteDocument, useProcessDocument, useUploadAndProcessDocument } from "@/hooks/use-documents";

function setup<T>(hook: () => T) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const remove = vi.spyOn(client, "removeQueries");
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  return { ...renderHook(hook, { wrapper }), invalidate, remove };
}

describe("document mutation query refresh", () => {
  beforeEach(() => { mocks.upload.mockReset().mockResolvedValue({ id: "doc-1" }); mocks.process.mockReset().mockResolvedValue({ id: "doc-1" }); mocks.reprocess.mockReset().mockResolvedValue({ id: "doc-1" }); mocks.remove.mockReset().mockResolvedValue(undefined); });
  it("refreshes list and detail queries after upload and processing", async () => { const { result, invalidate } = setup(useUploadAndProcessDocument); await act(() => result.current.mutateAsync({ title: "Guide", file: new File(["x"], "guide.txt") })); expect(mocks.upload).toHaveBeenCalledWith("access-token", "Guide", expect.any(File)); expect(mocks.process).toHaveBeenCalledWith("access-token", "doc-1"); expect(invalidate).toHaveBeenCalledWith({ queryKey: ["documents"] }); expect(invalidate).toHaveBeenCalledWith({ queryKey: ["document", "doc-1"] }); });
  it("refreshes document, list, and chunks after reprocessing", async () => { const { result, invalidate } = setup(() => useProcessDocument("doc-1", true)); await act(() => result.current.mutateAsync()); expect(mocks.reprocess).toHaveBeenCalledWith("access-token", "doc-1"); expect(invalidate).toHaveBeenCalledWith({ queryKey: ["documents"] }); expect(invalidate).toHaveBeenCalledWith({ queryKey: ["document-chunks", "doc-1"] }); });
  it("removes detail caches and refreshes the list after delete", async () => { const { result, invalidate, remove } = setup(() => useDeleteDocument("doc-1")); await act(() => result.current.mutateAsync()); expect(remove).toHaveBeenCalledWith({ queryKey: ["document", "doc-1"] }); expect(invalidate).toHaveBeenCalledWith({ queryKey: ["documents"] }); });
});
