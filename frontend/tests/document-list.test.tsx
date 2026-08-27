import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { KnowledgeDocument } from "@/types/api";

const mocks = vi.hoisted(() => ({
  params: "",
  push: vi.fn(), replace: vi.fn(), refetch: vi.fn(), mutateAsync: vi.fn(),
  documents: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push, replace: mocks.replace }), usePathname: () => "/knowledge-base", useSearchParams: () => new URLSearchParams(mocks.params) }));
vi.mock("@/hooks/use-documents", () => ({
  useDocuments: (filters: unknown) => mocks.documents(filters),
  useDeleteDocument: () => ({ mutateAsync: mocks.mutateAsync, isPending: false }),
  useUploadAndProcessDocument: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { DocumentList } from "@/components/documents/document-list";

const document: KnowledgeDocument = { id: "doc-1", title: "Support guide", original_filename: "support.md", storage_bucket: "private", file_type: "markdown", mime_type: "text/markdown", file_size_bytes: 2048, checksum_sha256: "hash", status: "completed", version: 2, chunk_count: 7, uploaded_by: "user-1", created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z", processed_at: "2026-08-20T00:01:00Z" };
const loaded = { isLoading: false, isError: false, data: { items: [document], total: 21, page: 1, page_size: 10 }, refetch: mocks.refetch };

describe("DocumentList", () => {
  beforeEach(() => { mocks.params = ""; mocks.push.mockReset(); mocks.replace.mockReset(); mocks.refetch.mockReset(); mocks.mutateAsync.mockReset().mockResolvedValue(undefined); mocks.documents.mockReset().mockReturnValue(loaded); });
  it("renders the loading skeleton", () => { mocks.documents.mockReturnValue({ isLoading: true }); render(<DocumentList />); expect(screen.getByLabelText("Loading documents")).toBeInTheDocument(); });
  it("renders the empty knowledge base state", () => { mocks.documents.mockReturnValue({ ...loaded, data: { items: [], total: 0, page: 1, page_size: 10 } }); render(<DocumentList />); expect(screen.getByText("Your knowledge base is empty")).toBeInTheDocument(); });
  it("renders the no-results state for active filters", () => { mocks.params = "status=failed"; mocks.documents.mockReturnValue({ ...loaded, data: { items: [], total: 0, page: 1, page_size: 10 } }); render(<DocumentList />); expect(screen.getByText("No documents match your filters")).toBeInTheDocument(); });
  it("renders an API error and retries", async () => { const user = userEvent.setup(); mocks.documents.mockReturnValue({ isLoading: false, isError: true, refetch: mocks.refetch }); render(<DocumentList />); await user.click(screen.getByRole("button", { name: "Retry" })); expect(mocks.refetch).toHaveBeenCalledOnce(); });
  it("renders document data and consistent status badges", () => { render(<DocumentList />); expect(screen.getAllByText("Support guide").length).toBeGreaterThan(0); expect(screen.getAllByLabelText("Status: Completed").length).toBeGreaterThan(0); expect(screen.getAllByText("7").length).toBeGreaterThan(0); });
  it("updates status and file-type URL filters", async () => { const user = userEvent.setup(); render(<DocumentList />); await user.selectOptions(screen.getByLabelText("Status filter"), "completed"); expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("status=completed")); await user.selectOptions(screen.getByLabelText("File type filter"), "pdf"); expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("file_type=pdf")); });
  it("debounces search into the URL", async () => { render(<DocumentList />); fireEvent.change(screen.getByLabelText("Search documents"), { target: { value: "policy" } }); await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("search=policy"))); });
  it("paginates and clears filters", async () => { const user = userEvent.setup(); mocks.params = "status=completed"; render(<DocumentList />); await user.click(screen.getByRole("button", { name: "Next" })); expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("page=2")); await user.click(screen.getByRole("button", { name: "Clear filters" })); expect(mocks.push).toHaveBeenCalledWith("/knowledge-base"); });
  it("confirms and completes deletion", async () => { const user = userEvent.setup(); render(<DocumentList />); await user.click(screen.getAllByRole("button", { name: "Delete" })[0]); expect(screen.getByRole("alertdialog")).toHaveTextContent("Support guide"); await user.click(screen.getByRole("button", { name: "Delete document" })); await waitFor(() => expect(mocks.mutateAsync).toHaveBeenCalledOnce()); expect(screen.getByRole("status")).toHaveTextContent("Document deleted"); });
  it("keeps the confirmation open on delete failure", async () => { const user = userEvent.setup(); mocks.mutateAsync.mockRejectedValue(new Error("storage")); render(<DocumentList />); await user.click(screen.getAllByRole("button", { name: "Delete" })[0]); await user.click(screen.getByRole("button", { name: "Delete document" })); expect(await screen.findByRole("alert")).toHaveTextContent("could not be deleted"); });
});
