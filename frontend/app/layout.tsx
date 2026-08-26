import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudDesk Support Workspace",
  description: "Internal workspace for CloudDesk support teams.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
