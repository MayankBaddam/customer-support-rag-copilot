import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiErrorState } from "@/components/errors/api-error-state";
import { ApiClientError } from "@/lib/api-client";

describe("ApiErrorState", () => {
  it.each([
    [401, "Your session has expired", "Sign in again to continue."],
    [403, "Access denied", "You do not have permission to access this resource."],
    [404, "Resource not found", "The requested resource is unavailable or has been removed."],
    [429, "Request limit reached", "Please wait a moment before trying again."],
    [500, "Service unavailable", "The server could not complete the request. Please try again."],
  ])("displays a safe state for HTTP %i", (status, title, message) => {
    render(<ApiErrorState error={new ApiClientError("private backend detail", status)} fallbackTitle="Fallback" fallbackMessage="Fallback message" />);

    expect(screen.getByRole("alert")).toHaveTextContent(title);
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByText("private backend detail")).not.toBeInTheDocument();
    if (status === 401) expect(screen.getByRole("link", { name: "Return to sign in" })).toHaveAttribute("href", "/login");
  });

  it("displays a network failure state", () => {
    render(<ApiErrorState error={new ApiClientError("The backend could not be reached.")} fallbackTitle="Fallback" fallbackMessage="Fallback message" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Backend unavailable");
    expect(screen.getByText("Check your network connection and try again.")).toBeInTheDocument();
  });
});
