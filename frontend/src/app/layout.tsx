import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "DataBoom",
  description:
    "Synthetic data platform for relational, document, graph, and masking workflows.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
