import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { KnowledgeDocument } from "@/types/api";

const mocks = vi.hoisted(() => ({ replace: vi.fn(), refetch: vi.fn(), process: vi.fn(), reprocess: vi.fn(), remove: vi.fn(), chunkRefetch: vi.fn(), documentQuery: {} as Record<string, unknown>, chunksQuery: {} as Record<string, unknown> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("@/hooks/use-documents", () => ({
  useDocument: () => mocks.documentQuery,
  useProcessDocument: (_id: string, again: boolean) => ({ mutateAsync: again ? mocks.reprocess : mocks.process, isPending: false }),
  useDeleteDocument: () => ({ mutateAsync: mocks.remove, isPending: false }),
  useDocumentChunks: () => mocks.chunksQuery,
}));
import { DocumentDetail } from "@/components/documents/document-detail";

const baseDocument: KnowledgeDocument = { id: "doc-1", title: "Support handbook", original_filename: "handbook.pdf", storage_bucket: "private", file_type: "pdf", mime_type: "application/pdf", file_size_bytes: 4096, checksum_sha256: "hash", status: "completed", version: 3, chunk_count: 12, uploaded_by: "user-1", created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z", processed_at: "2026-08-20T00:01:00Z" };
const longContent = "A".repeat(500);

describe("DocumentDetail", () => {
  beforeEach(() => {
    mocks.replace.mockReset(); mocks.refetch.mockReset(); mocks.process.mockReset().mockResolvedValue(baseDocument); mocks.reprocess.mockReset().mockResolvedValue(baseDocument); mocks.remove.mockReset().mockResolvedValue(undefined); mocks.chunkRefetch.mockReset();
    mocks.documentQuery = { isLoading: false, isError: false, data: baseDocument, refetch: mocks.refetch };
    mocks.chunksQuery = { isLoading: false, isError: false, data: { items: [{ id: "chunk-1", document_id: "doc-1", chunk_index: 0, content: longContent, section_title: "Getting started", page_number: 2, token_count: 120, metadata: {}, created_at: "2026-08-20T00:00:00Z" }], total: 21, page: 1, page_size: 10 }, refetch: mocks.chunkRefetch };
  });
  it("renders document details and chunk metadata", () => { render(<DocumentDetail documentId="doc-1" />); expect(screen.getByRole("heading", { level: 1, name: "Support handbook" })).toBeInTheDocument(); expect(screen.getAllByText("handbook.pdf").length).toBeGreaterThan(0); expect(screen.getByText("Getting started")).toBeInTheDocument(); expect(screen.getByText("Page 2")).toBeInTheDocument(); expect(screen.getByText("120 tokens")).toBeInTheDocument(); });
  it("expands and collapses long chunk content", async () => { const user = userEvent.setup(); render(<DocumentDetail documentId="doc-1" />); const button = screen.getByRole("button", { name: "Show more" }); expect(screen.queryByText(longContent)).not.toBeInTheDocument(); await user.click(button); expect(screen.getByText(longContent)).toBeInTheDocument(); await user.click(screen.getByRole("button", { name: "Show less" })); expect(screen.queryByText(longContent)).not.toBeInTheDocument(); });
  it("paginates chunks", async () => { const user = userEvent.setup(); render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Next chunks" })); expect(screen.getByText("Page 2 of 3")).toBeInTheDocument(); });
  it("processes a pending document", async () => { const user = userEvent.setup(); mocks.documentQuery = { ...mocks.documentQuery, data: { ...baseDocument, status: "pending", processed_at: null } }; render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Process document" })); await waitFor(() => expect(mocks.process).toHaveBeenCalledOnce()); expect(screen.getByRole("status")).toHaveTextContent("processed successfully"); });
  it("reprocesses a completed document", async () => { const user = userEvent.setup(); render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Reprocess document" })); expect(mocks.reprocess).toHaveBeenCalledOnce(); });
  it("shows a safe failed status message", () => { mocks.documentQuery = { ...mocks.documentQuery, data: { ...baseDocument, status: "failed" } }; render(<DocumentDetail documentId="doc-1" />); expect(screen.getByRole("alert")).toHaveTextContent("Review the source file"); });
  it("refreshes status on demand", async () => { const user = userEvent.setup(); render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Refresh status" })); expect(mocks.refetch).toHaveBeenCalledOnce(); });
  it("confirms deletion and redirects after success", async () => { const user = userEvent.setup(); render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Delete document" })); const dialog = screen.getByRole("alertdialog"); expect(dialog).toHaveTextContent("Support handbook"); await user.click(within(dialog).getByRole("button", { name: "Delete document" })); await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/knowledge-base")); });
  it("shows a safe delete failure without redirecting", async () => { const user = userEvent.setup(); mocks.remove.mockRejectedValue(new Error("storage secret")); render(<DocumentDetail documentId="doc-1" />); await user.click(screen.getByRole("button", { name: "Delete document" })); await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete document" })); expect(await screen.findByRole("alert")).toHaveTextContent("could not be deleted"); expect(mocks.replace).not.toHaveBeenCalled(); });
});
