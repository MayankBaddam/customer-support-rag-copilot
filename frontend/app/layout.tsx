import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { QueryProvider } from "@/components/query-provider";

export const metadata: Metadata = {
  title: "CloudDesk Support Workspace",
  description: "Internal workspace for CloudDesk support teams.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="antialiased"><QueryProvider><AuthProvider>{children}</AuthProvider></QueryProvider></body>
    </html>
  );
}
