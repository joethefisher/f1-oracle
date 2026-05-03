"use client";
import { useState } from "react";
import type { RaceRecord, MarketType, Race } from "@/lib/types";
import { StatCard, BetBadge, MarketBadge, SectionCard, Edge } from "@/app/components/ui";

const MONO = "var(--font-geist-mono), ui-monospace, monospace";

const MARKET_LABELS: Record<MarketType, string> = {
  race_winner: "WIN",
  podium: "PODIUM",
  pole: "POLE",
  sprint: "SPRINT",
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function RecordView({ records, season, activeRace, totalRaces }: { records: RaceRecord[]; season?: number; activeRace?: Race | null; totalRaces?: number }) {
  const firstId = records[0]?.race.id;
  const [open, setOpen] = useState<Set<number>>(
    firstId !== undefined ? new Set([firstId]) : new Set()
  );

  const toggle = (id: number) => {
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const totalBets = records.reduce((s, r) => s + r.n_bets, 0);
  const totalWins = records.reduce((s, r) => s + r.n_wins, 0);
  const totalPnl  = records.reduce((s, r) => s + r.total_pnl, 0);
  const hitRate   = totalBets > 0 ? ((totalWins / totalBets) * 100).toFixed(0) : "0";

  const headerCell: React.CSSProperties = {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.14em",
    color: "#71717A",
    fontWeight: 500,
    padding: "10px 16px",
    background: "#08080A",
    borderBottom: "1px solid #1F1F23",
    textAlign: "left",
  };

  const seasonYear = season ?? records[0]?.race.season ?? new Date().getFullYear();

  if (records.length === 0) {
    return (
      <div>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em", margin: 0, color: "#FAFAFA", marginBottom: 6 }}>
          Season Record
        </h1>
        <div style={{ fontSize: 13, color: "#71717A", marginBottom: 22 }}>{seasonYear} season · 0 of {totalRaces || "?"} races settled</div>
        <div style={{ background: "#0E0E10", border: "1px solid #1F1F23", borderRadius: 8, padding: "40px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 28, marginBottom: 10 }}>🏁</div>
          <div style={{ fontSize: 15, fontWeight: 500, color: "#FAFAFA", marginBottom: 8 }}>
            No settled races yet
          </div>
          <div style={{ fontSize: 13, color: "#71717A", maxWidth: 360, margin: "0 auto", lineHeight: 1.6 }}>
            {activeRace
              ? <>Bet results will appear here after <span style={{ color: "#D4D4D8" }}>{activeRace.name}</span> settles. Check back after the race.</>
              : "Bet results will appear here after the first race of the season settles."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em", margin: 0, color: "#FAFAFA", marginBottom: 6 }}>
        Season Record
      </h1>
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 22 }}>
        {seasonYear} season · {records.length} of {totalRaces || "?"} races settled
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
        <StatCard
          label="Bets"
          value={String(totalBets)}
          sub={`across ${records.length} race${records.length !== 1 ? "s" : ""}`}
        />
        <StatCard
          label="Hit Rate"
          value={`${hitRate}%`}
          sub={`${totalWins} wins · ${totalBets - totalWins} losses`}
        />
        <StatCard
          label="Virtual P&L"
          value={`${totalPnl >= 0 ? "+" : "−"}$${Math.abs(totalPnl).toFixed(2)}`}
          valueColor={totalPnl >= 0 ? "#34D399" : "#F87171"}
          sub={`${totalPnl >= 0 ? "+" : ""}${((totalPnl / 1000) * 100).toFixed(2)}% on $1,000`}
        />
      </div>

      {/* Accordion list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {records.map((record) => {
          const isOpen = open.has(record.race.id);
          const pnl = record.total_pnl;
          return (
            <SectionCard key={record.race.id}>
              {/* Header row */}
              <div
                onClick={() => toggle(record.race.id)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "60px 1fr 160px 80px 110px 24px",
                  alignItems: "center",
                  padding: "16px 20px",
                  background: isOpen ? "#131316" : "#0E0E10",
                  cursor: "pointer",
                  gap: 12,
                }}
              >
                <span style={{ fontFamily: MONO, color: "#52525B", fontSize: 12, fontWeight: 600, letterSpacing: "0.04em" }}>
                  R{record.race.round}
                </span>
                <span style={{ color: "#FAFAFA", fontWeight: 500, fontSize: 15 }}>{record.race.name}</span>
                <span style={{ color: "#71717A", fontSize: 12 }}>{formatDate(record.race.race_date_utc)}</span>
                <span style={{ color: "#A1A1AA", fontSize: 13, fontFamily: MONO }}>
                  {record.n_wins}/{record.n_bets}
                </span>
                <span style={{ color: pnl >= 0 ? "#34D399" : "#F87171", fontSize: 14, fontWeight: 600, fontFamily: MONO, fontVariantNumeric: "tabular-nums", textAlign: "right" }}>
                  {pnl >= 0 ? "+" : "−"}${Math.abs(pnl).toFixed(2)}
                </span>
                <span style={{ color: "#52525B", fontSize: 14, textAlign: "center", transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s", display: "inline-block" }}>
                  ▾
                </span>
              </div>

              {/* Expanded detail */}
              {isOpen && record.bets.length > 0 && (
                <table style={{ width: "100%", borderCollapse: "collapse", background: "#08080A" }}>
                  <thead>
                    <tr>
                      <th style={headerCell}>Driver</th>
                      <th style={{ ...headerCell, width: 80 }}>Market</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Oracle</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Kalshi</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Edge</th>
                      <th style={{ ...headerCell, width: 90, textAlign: "right" }}>Bet Size</th>
                      <th style={{ ...headerCell, width: 90 }}>Result</th>
                      <th style={{ ...headerCell, width: 100, textAlign: "right" }}>P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {record.bets.map((bet, j) => (
                      <tr key={j} style={{ borderBottom: j === record.bets.length - 1 ? "none" : "1px solid #15151A" }}>
                        <td style={{ padding: "12px 16px", color: "#FAFAFA", fontSize: 13 }}>{bet.driver_name}</td>
                        <td style={{ padding: "12px 16px" }}>
                          <MarketBadge>{MARKET_LABELS[bet.market_type]}</MarketBadge>
                        </td>
                        <td style={{ padding: "12px 16px", color: "#FAFAFA", fontFamily: MONO, fontSize: 12, textAlign: "right" }}>
                          {(bet.oracle_probability * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: "12px 16px", color: "#71717A", fontFamily: MONO, fontSize: 12, textAlign: "right" }}>
                          {(bet.kalshi_mid_price * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: "12px 16px", textAlign: "right" }}>
                          <Edge valuePct={bet.edge * 100} />
                        </td>
                        <td style={{ padding: "12px 16px", color: "#D4D4D8", fontFamily: MONO, fontSize: 12, textAlign: "right" }}>
                          ${bet.bet_size_dollars.toFixed(2)}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <span style={{ color: bet.won ? "#34D399" : "#F87171", fontSize: 12, fontWeight: 600, fontFamily: MONO, letterSpacing: "0.04em" }}>
                            {bet.won ? "WIN ✓" : "LOSS ✗"}
                          </span>
                        </td>
                        <td style={{ padding: "12px 16px", color: bet.pnl >= 0 ? "#34D399" : "#F87171", fontFamily: MONO, fontSize: 12, fontWeight: 600, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {bet.pnl >= 0 ? "+" : "−"}${Math.abs(bet.pnl).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </SectionCard>
          );
        })}
      </div>
    </div>
  );
}
