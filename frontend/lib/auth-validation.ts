export type AuthFormValues = { email: string; password: string; fullName?: string };

export function validateAuthForm(values: AuthFormValues, registration = false): string | null {
  if (registration && !values.fullName?.trim()) return "Enter your full name.";
  if (!values.email.trim() || !values.email.includes("@")) return "Enter a valid email address.";
  if (values.password.length < 8) return "Password must be at least 8 characters.";
  return null;
}