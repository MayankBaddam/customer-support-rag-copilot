import { describe, expect, it } from "vitest";
import { validateAuthForm } from "@/lib/auth-validation";

describe("auth form validation", () => {
  it("rejects invalid login values", () => {
    expect(validateAuthForm({ email: "invalid", password: "short" })).toBe("Enter a valid email address.");
  });

  it("requires a name when registering", () => {
    expect(validateAuthForm({ email: "agent@example.test", password: "password123" }, true)).toBe("Enter your full name.");
  });

  it("accepts valid registration values", () => {
    expect(validateAuthForm({ email: "agent@example.test", password: "password123", fullName: "Demo Agent" }, true)).toBeNull();
  });
});