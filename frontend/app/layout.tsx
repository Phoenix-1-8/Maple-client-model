import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";

export const metadata: Metadata = {
  title: "Maple Store · AI Department",
  description:
    "AI-driven pricing intelligence for the Indian pre-owned iPhone market.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
