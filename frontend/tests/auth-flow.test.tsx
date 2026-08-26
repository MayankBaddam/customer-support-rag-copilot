import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { replace, signOut, getSession, unsubscribe } = vi.hoisted(() => ({
  replace: vi.fn(),
  signOut: vi.fn().mockResolvedValue({ error: null }),
  getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
  unsubscribe: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace }),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession,
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe } } }),
      signOut,
    },
  },
}));

import { AuthProvider } from "@/components/auth/auth-provider";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";

describe("protected authentication flow", () => {
  beforeEach(() => {
    replace.mockReset();
    signOut.mockClear();
    getSession.mockClear();
  });

  it("redirects a signed-out user to login", async () => {
    render(<AuthProvider><AppShell><p>Protected content</p></AppShell></AuthProvider>);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("clears the Supabase session on logout", async () => {
    const user = userEvent.setup();
    render(<AuthProvider><Header><span>status</span></Header></AuthProvider>);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(signOut).toHaveBeenCalledOnce();
    expect(replace).toHaveBeenCalledWith("/login");
  });
});