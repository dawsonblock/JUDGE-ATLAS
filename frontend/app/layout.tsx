import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "JudgeTracker Atlas",
  description: "Runnable prototype for court-event legal intelligence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}

