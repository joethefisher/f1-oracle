import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TabNav } from "./components/TabNav";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://joeking.ai/f1-oracle"),
  title: "F1 Oracle — ML predictions vs Kalshi F1 markets",
  description:
    "F1 Oracle is a calibrated logistic-regression + Elo Formula 1 prediction model. Predictions are bet at half-Kelly against Kalshi prices and self-graded against actual race results.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "F1 Oracle",
    description: "Calibrated ML predictions vs Kalshi F1 markets. Self-graded.",
    type: "website",
    url: "/",
    siteName: "F1 Oracle",
  },
  twitter: {
    card: "summary",
    title: "F1 Oracle",
    description: "Calibrated ML predictions vs Kalshi F1 markets. Self-graded.",
  },
};

// schema.org WebSite — sitelinks + brand-name disambiguation eligibility.
const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "F1 Oracle",
  url: "https://joeking.ai/f1-oracle",
  description:
    "Calibrated logistic-regression + Elo Formula 1 prediction model. Predictions placed at half-Kelly against Kalshi markets and graded against actual race outcomes.",
  keywords: [
    "F1 predictions",
    "Formula 1 betting model",
    "Kalshi F1",
    "race winner prediction",
    "qualifying prediction",
    "Elo ratings F1",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col" style={{ background: "#100D0B", color: "#FAFAFA" }}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
        />
        <header style={{ background: "#100D0B" }}>
          <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 32px 0" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                <span style={{ fontWeight: 800, fontSize: 26, color: "#E8002D", letterSpacing: "-0.02em", lineHeight: 1 }}>F1</span>
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
