import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BioIntelligence",
  description:
    "Precision AI / Evidence-Based Health Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <header className="border-b border-border/40 py-4">
          <div className="mx-auto max-w-2xl px-4">
            <h1 className="text-xl font-bold tracking-tight">
              BioIntelligence
            </h1>
            <p className="text-sm text-muted-foreground">
              Precision AI / Evidence-Based Health Intelligence
            </p>
          </div>
        </header>

        <main className="flex-1">
          <div className="mx-auto max-w-2xl px-4 py-6">{children}</div>
        </main>

        <footer className="border-t border-border/40 py-4">
          <div className="mx-auto max-w-2xl px-4">
            <p className="text-xs text-muted-foreground text-center">
              AI research tool, not a medical service. Does not diagnose, treat,
              or replace clinical care.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
