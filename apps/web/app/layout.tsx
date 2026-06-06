import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PortalPilot",
  description: "Agent workqueue for government filings",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
