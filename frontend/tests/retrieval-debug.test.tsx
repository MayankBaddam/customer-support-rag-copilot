import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ search: vi.fn() }));

vi.mock("@/hooks/use-semantic-search", async () => {
  const { useState } = await import("react");
  return { useSemanticSearch: () => {
    const [state, setState] = useState({ isPending: false, isError: false, isSuccess: false, data: undefined as typeof successfulResponse | undefined, error: null as Error | null });
    return {
      ...state,
      mutateAsync: async (request: { query: string; top_k: number }) => {
        setState({ isPending: true, isError: false, isSuccess: false, data: undefined, error: null });
        try {
          const data = await mocks.search(request);
          if (data.testError) {
            setState({ isPending: false, isError: true, isSuccess: false, data: undefined, error: data.testError });
            return undefined;
          }
          setState({ isPending: false, isError: false, isSuccess: true, data, error: null });
          return data;
        } catch (error) {
          setState({ isPending: false, isError: true, isSuccess: false, data: undefined, error: error as Error });
          return undefined;
        }
      },
    };
  } };
});

import { ApiClientError } from "@/lib/api-client";
import { RetrievalDebug } from "@/components/retrieval/retrieval-debug";

const successfulResponse = {
  request_id: "request-1",
  query: "How long is recovery valid?",
  result_count: 1,
  retrieval_latency_ms: 12.34,
  embedding_model: "gemini-embedding-001",
  evidence_status: "found" as const,
  results: [{
    chunk_id: "chunk-1",
    document_id: "document-1",
    document_title: "Account recovery",
    original_filename: "account-recovery.md",
    section_title: "Recovery links",
    page_number: 2,
    content: "Password recovery links remain valid for thirty minutes.",
    similarity_score: 0.9123,
  }],
};

function renderDebug() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  return render(<RetrievalDebug />, { wrapper });
}

describe("RetrievalDebug", () => {
  beforeEach(() => mocks.search.mockReset());

  it("runs a successful authenticated search and renders evidence metadata", async () => {
    mocks.search.mockResolvedValue(successfulResponse);
    const user = userEvent.setup();
    renderDebug();

    await user.type(screen.getByLabelText("Search query"), "How long is recovery valid?");
    await user.selectOptions(screen.getByLabelText("Top results"), "3");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(screen.getByText("Account recovery")).toBeInTheDocument());
    expect(mocks.search).toHaveBeenCalledWith({ query: "How long is recovery valid?", top_k: 3 });
    expect(screen.getByText("account-recovery.md")).toBeInTheDocument();
    expect(screen.getByText("Section: Recovery links")).toBeInTheDocument();
    expect(screen.getByText("Page: 2")).toBeInTheDocument();
    expect(screen.getByText("0.9123")).toBeInTheDocument();
    expect(screen.getByText("12.34 ms")).toBeInTheDocument();
    expect(screen.getByText(successfulResponse.results[0].content)).toBeInTheDocument();
    expect(screen.queryByText(/vector/i)).not.toBeInTheDocument();
  });

  it("disables search for an empty or whitespace-only query", async () => {
    const user = userEvent.setup();
    renderDebug();
    const button = screen.getByRole("button", { name: "Search" });

    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Search query"), "   ");
    expect(button).toBeDisabled();
    expect(mocks.search).not.toHaveBeenCalled();
  });

  it("renders a safe API error state", async () => {
    mocks.search.mockResolvedValue({ testError: new ApiClientError("Internal provider detail", 503) });
    const user = userEvent.setup();
    renderDebug();

    await user.type(screen.getByLabelText("Search query"), "recovery");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Search could not be completed");
    expect(screen.queryByText("Internal provider detail")).not.toBeInTheDocument();
  });

  it("renders an empty-results state", async () => {
    mocks.search.mockResolvedValue({ ...successfulResponse, results: [], result_count: 0, evidence_status: "no_evidence" });
    const user = userEvent.setup();
    renderDebug();

    await user.type(screen.getByLabelText("Search query"), "unknown policy");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("No matching evidence")).toBeInTheDocument();
  });

  it("renders an unauthorized session state without exposing the token", async () => {
    mocks.search.mockResolvedValue({ testError: new ApiClientError("Authentication required.", 401) });
    const user = userEvent.setup();
    renderDebug();

    await user.type(screen.getByLabelText("Search query"), "recovery");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Your session has expired")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return to sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("access-token")).not.toBeInTheDocument();
  });
});
