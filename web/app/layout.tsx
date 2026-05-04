import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TabNav } from "./components/TabNav";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "F1 Oracle",
  description: "ML predictions vs Kalshi markets for F1 race weekends",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col" style={{ background: "#100D0B", color: "#FAFAFA" }}>
        <header style={{ background: "#100D0B" }}>
          <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 32px 0" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <img src="/f1-oracle/F1.svg" alt="F1" style={{ height: 22, width: "auto" }} />
                <span style={{ fontWeight: 600, fontSize: 26, color: "#FAFAFA", letterSpacing: "-0.02em", lineHeight: 1 }}>Oracle</span>
              </div>
              <span style={{ color: "#52525B", fontSize: 13 }}>ML Model vs Kalshi F1 Fans</span>
            </div>
          </div>
        </header>
        <TabNav />
        <main className="flex-1" style={{ maxWidth: 1100, margin: "0 auto", width: "100%", padding: "28px 32px 48px" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
