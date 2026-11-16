import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Lumina — Retrieval Workspace",
  icons: {
    icon: { url: "/images/logo.png", type: "image/png" },
    shortcut: "/images/logo.png",
    apple: "/images/logo.png",
  },
  description:
    "Không gian khám phá tài liệu và trình diễn Agentic RAG · Lab 07",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
