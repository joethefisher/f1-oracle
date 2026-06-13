import type { Metadata } from "next";
import { getPortfolioSnapshots, getActiveRace } from "@/lib/queries";
import PortfolioChart from "./PortfolioChart";
import { StatCard, SectionCard } from "@/app/components/ui";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Portfolio — F1 Oracle",
  description:
    "F1 Oracle's running half-Kelly portfolio against Kalshi F1 markets. Bankroll, edge, hit rate, and per-race PnL.",
  alternates: { canonical: "/portfolio" },
  openGraph: {
    title: "Portfolio — F1 Oracle",
    description: "Half-Kelly portfolio performance vs Kalshi F1 markets.",
    url: "/portfolio",
    type: "website",
  },
};

const STARTING = 1000.0;
const MONO = "var(--font-geist-mono), ui-monospace, monospace";

export default async function PortfolioPage() {
  const [snapshots, activeRace] = await Promise.all([
    getPortfolioSnapshots(),
    getActiveRace(),
  ]);

  const latest = snapshots[snapshots.length - 1];
  const portfolioValue = latest?.bankroll_after ?? STARTING;
  const returnPct = ((portfolioValue - STARTING) / STARTING) * 100;
  const baselineReturn = latest
    ? ((latest.kalshi_baseline_value - STARTING) / STARTING) * 100
    : 0;

  const headerCell: React.CSSProperties = {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.14em",
    color: "#71717A",
    fontWeight: 500,
    padding: "12px 20px",
    background: "#131316",
    borderBottom: "1px solid #1F1F23",
    textAlign: "left",
  };

  return (
    <div>
      {/* Header */}
      <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em", margin: 0, color: "#FAFAFA", marginBottom: 6 }}>
        Portfolio
      </h1>
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 22 }}>
        Virtual $1,000 starting bankroll · Kelly-fractional sizing · No real money
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
        <StatCard
          label="Portfolio Value"
          value={snapshots.length > 0 ? `$${portfolioValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "$1,000.00"}
          sub="Started at $1,000.00"
          style={{ flex: "0 0 32%" }}
        />
        <StatCard
          label="Oracle Return"
          value={snapshots.length > 0 ? `${returnPct >= 0 ? "+" : ""}${returnPct.toFixed(2)}%` : "—"}
          valueColor={snapshots.length > 0 ? (returnPct >= 0 ? "#34D399" : "#F87171") : "#52525B"}
          sub={snapshots.length > 0 ? `vs Kalshi avg ${baselineReturn >= 0 ? "+" : ""}${baselineReturn.toFixed(2)}%` : "No settled races yet"}
        />
        <StatCard
          label="Kalshi Avg Return"
          value={snapshots.length > 0 ? `${baselineReturn >= 0 ? "+" : ""}${baselineReturn.toFixed(2)}%` : "—"}
          valueColor={snapshots.length > 0 ? (baselineReturn >= 0 ? "#34D399" : "#F87171") : "#52525B"}
          sub="Crowd-weighted baseline"
        />
        <StatCard
          label="Races Played"
          value={String(snapshots.length)}
          sub="of 24 in 2026 season"
        />
      </div>

      {snapshots.length === 0 ? (
        <div style={{ background: "#0E0E10", border: "1px solid #1F1F23", borderRadius: 8, padding: "40px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 28, marginBottom: 10 }}>📈</div>
          <div style={{ fontSize: 15, fontWeight: 500, color: "#FAFAFA", marginBottom: 8 }}>
            No settled races yet
          </div>
          <div style={{ fontSize: 13, color: "#71717A", maxWidth: 360, margin: "0 auto", lineHeight: 1.6 }}>
            {activeRace
              ? <>Portfolio performance will appear here after <span style={{ color: "#D4D4D8" }}>{activeRace.name}</span> settles. Check back after the race.</>
              : "Portfolio performance will appear here after the first race of the season settles."}
          </div>
        </div>
      ) : (
        <>
          {/* Chart card */}
          <SectionCard style={{ marginBottom: 22, padding: "20px 0 8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "0 24px 12px" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#FAFAFA", marginBottom: 4 }}>Cumulative performance</div>
                <div style={{ fontSize: 12, color: "#71717A" }}>$ value across the 2026 season</div>
              </div>
              <div style={{ display: "flex", gap: 18, fontSize: 12, alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ width: 14, height: 2, background: "#E8002D", display: "inline-block" }} />
                  <span style={{ color: "#D4D4D8" }}>Oracle</span>
                  <span style={{ color: "#71717A", fontFamily: MONO }}>${portfolioValue.toFixed(2)}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ width: 14, height: 0, border: "1px dashed #71717A", display: "inline-block" }} />
                  <span style={{ color: "#D4D4D8" }}>Kalshi avg</span>
                  <span style={{ color: "#71717A", fontFamily: MONO }}>${(latest?.kalshi_baseline_value ?? STARTING).toFixed(2)}</span>
                </div>
              </div>
            </div>
            <PortfolioChart snapshots={snapshots} />
          </SectionCard>

          {/* History table */}
          <SectionCard>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={headerCell}>Race</th>
                  <th style={{ ...headerCell, textAlign: "right" }}>Oracle Portfolio</th>
                  <th style={{ ...headerCell, textAlign: "right" }}>Race Return</th>
                  <th style={{ ...headerCell, textAlign: "right" }}>Kalshi Avg</th>
                </tr>
              </thead>
              <tbody>
                {[...snapshots].reverse().map((snap, i, arr) => (
                  <tr key={snap.id} style={{ borderBottom: i === arr.length - 1 ? "none" : "1px solid #15151A", background: i % 2 === 0 ? "#0A0A0A" : "#0C0C0E" }}>
                    <td style={{ padding: "14px 20px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ color: "#FAFAFA", fontSize: 14 }}>
                          {snap.race_name.replace(" Grand Prix", " GP")}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "14px 20px", textAlign: "right", color: "#FAFAFA", fontFamily: MONO, fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                      ${snap.bankroll_after.toFixed(2)}
                    </td>
                    <td style={{ padding: "14px 20px", textAlign: "right" }}>
                      <span style={{ color: snap.return_pct >= 0 ? "#34D399" : "#F87171", fontFamily: MONO, fontSize: 13, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                        {snap.return_pct >= 0 ? "+" : ""}{snap.return_pct.toFixed(2)}%
                      </span>
                    </td>
                    <td style={{ padding: "14px 20px", textAlign: "right", color: "#71717A", fontFamily: MONO, fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                      ${snap.kalshi_baseline_value.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </SectionCard>
        </>
      )}
    </div>
  );
}
