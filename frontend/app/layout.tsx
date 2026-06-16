import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "AI vs Bookmakers — The Disagreement Engine",
  description:
    "Five AIs disagree before every World Cup match, commit their picks cryptographically, then get vindicated or humiliated — with receipts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
