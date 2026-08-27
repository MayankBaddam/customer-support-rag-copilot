import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ answer: vi.fn() }));

vi.mock("@/hooks/use-grounded-answer", async () => {
  const { useState } = await import("react");
  return { useGroundedAnswer: () => {
    const [state, setState] = useState({ isPending: false, isError: false, isSuccess: false, data: undefined as typeof successfulResponse | undefined, error: null as Error | null });
    return {
      ...state,
      mutateAsync: async (request: { query: string; top_k: number }) => {
        setState({ isPending: true, isError: false, isSuccess: false, data: undefined, error: null });
        const data = await mocks.answer(request);
        if (data.testError) {
          setState({ isPending: false, isError: true, isSuccess: false, data: undefined, error: data.testError });
          return undefined;
        }
        setState({ isPending: false, isError: false, isSuccess: true, data, error: null });
        return data;
      },
    };
  } };
});

import { CopilotChat } from "@/components/copilot/copilot-chat";
import { ApiClientError } from "@/lib/api-client";

const successfulResponse = {
  answer: "Password recovery links remain valid for thirty minutes.",
  retrieved_chunks: 1,
  citations: [{
    chunk_id: "chunk-1",
    document_title: "Account recovery",
    original_filename: "account-recovery.md",
    section_title: "Recovery links",
    page_number: 2,
    similarity_score: 0.9123,
  }],
};

function renderChat() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  return render(<CopilotChat />, { wrapper });
}

async function submitQuestion(question = "How long is recovery valid?") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Question"), question);
  await user.click(screen.getByRole("button", { name: "Ask Copilot" }));
}

describe("CopilotChat", () => {
  beforeEach(() => mocks.answer.mockReset());

  it("submits one question and displays the grounded answer", async () => {
    mocks.answer.mockResolvedValue(successfulResponse);
    renderChat();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Question"), "How long is recovery valid?");
    await user.selectOptions(screen.getByLabelText("Top sources"), "3");
    await user.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(await screen.findByText(successfulResponse.answer)).toBeInTheDocument();
    expect(mocks.answer).toHaveBeenCalledWith({ query: "How long is recovery valid?", top_k: 3 });
    expect(screen.getByText("Answers are based only on your uploaded knowledge documents.")).toBeInTheDocument();
  });

  it("disables submission for an empty or whitespace-only question", async () => {
    renderChat();
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: "Ask Copilot" });

    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Question"), "   ");
    expect(button).toBeDisabled();
    expect(mocks.answer).not.toHaveBeenCalled();
  });

  it("displays the backend insufficient-information answer without adding content", async () => {
    const message = "The knowledge base does not contain enough information to answer this question.";
    mocks.answer.mockResolvedValue({ answer: message, retrieved_chunks: 0, citations: [] });
    renderChat();

    await submitQuestion("What is the holiday policy?");

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText("No supporting citations")).toBeInTheDocument();
  });

  it("renders citation metadata without internal provider data", async () => {
    mocks.answer.mockResolvedValue(successfulResponse);
    renderChat();

    await submitQuestion();

    await waitFor(() => expect(screen.getByText("Account recovery")).toBeInTheDocument());
    expect(screen.getByText("account-recovery.md")).toBeInTheDocument();
    expect(screen.getByText("Section: Recovery links")).toBeInTheDocument();
    expect(screen.getByText("Page: 2")).toBeInTheDocument();
    expect(screen.getByText("0.9123")).toBeInTheDocument();
    expect(screen.queryByText(/embedding vector/i)).not.toBeInTheDocument();
  });

  it("renders a safe API error", async () => {
    mocks.answer.mockResolvedValue({ testError: new ApiClientError("Private provider detail", 503) });
    renderChat();

    await submitQuestion();

    expect(await screen.findByRole("alert")).toHaveTextContent("Copilot could not answer");
    expect(screen.queryByText("Private provider detail")).not.toBeInTheDocument();
  });

  it("renders an unauthorized state with a sign-in action", async () => {
    mocks.answer.mockResolvedValue({ testError: new ApiClientError("Authentication required.", 401) });
    renderChat();

    await submitQuestion();

    expect(await screen.findByText("Your session has expired")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return to sign in" })).toHaveAttribute("href", "/login");
  });
});
