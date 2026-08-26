export function validateTicketForm(values: { subject: string; customerName: string; customerEmail: string; initialMessage: string }): string | null {
  if (!values.subject.trim()) return "Subject is required.";
  if (!values.customerName.trim()) return "Customer name is required.";
  if (!values.customerEmail.includes("@")) return "Enter a valid customer email.";
  if (!values.initialMessage.trim()) return "Initial customer message is required.";
  return null;
}