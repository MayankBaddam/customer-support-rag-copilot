import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BackendStatus } from "@/components/layout/backend-status";

describe("BackendStatus", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows loading then online when health succeeds", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "ok", service: "api" }), { status: 200 }));
    render(<BackendStatus />);
    expect(screen.getByText("Checking backend")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Backend online")).toBeInTheDocument());
  });

  it("shows unavailable when health fails", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));
    render(<BackendStatus />);
    await waitFor(() => expect(screen.getByText("Backend unavailable")).toBeInTheDocument());
  });
});