import { describe, expect, it } from "vitest";
import { validateTicketForm } from "@/lib/ticket-validation";

describe("ticket form validation", () => {
  const valid = { subject: "Billing question", customerName: "Demo Customer", customerEmail: "customer@example.com", initialMessage: "Please help." };
  it("requires the ticket subject", () => expect(validateTicketForm({ ...valid, subject: "" })).toBe("Subject is required."));
  it("rejects invalid email addresses", () => expect(validateTicketForm({ ...valid, customerEmail: "invalid" })).toBe("Enter a valid customer email."));
  it("accepts a complete fictional ticket", () => expect(validateTicketForm(valid)).toBeNull());
});