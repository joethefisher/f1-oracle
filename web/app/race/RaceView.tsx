"use client";
import { useState } from "react";
import type { RacePredictionRow } from "@/lib/queries";
import type { MarketType, Race } from "@/lib/types";
import { BetBadge, SectionCard, ProbBar, Edge } from "@/app/components/ui";

const MONO = "var(--font-geist-mono), ui-monospace, monospace";

// Drivers whose Oracle rounds to 0.0% on display are hidden by default
const VISIBLE_THRESHOLD = 0.0005;

const MARKETS: { key: MarketType; label: string }[] = [
  { key: "race_winner", label: "Race Winner" },
  { key: "podium",      label: "Podium" },
  { key: "pole",        label: "Pole Position" },
];

function abbrevFromTicker(ticker: string): string {
  return ticker.split("-").pop() ?? "";
}

interface Props {
  race: Race;
  predictions: RacePredictionRow[];
}

export default function RaceView({ race, predictions }: Props) {
  const [market, setMarket] = useState<MarketType>("race_winner");
  const [showAll, setShowAll] = useState(false);

  const rows = predictions
    .filter((p) => p.market_type === market)
    .sort((a, b) => b.oracle_probability - a.oracle_probability);

  const visibleRows = rows.filter((r) => r.oracle_probability >= VISIBLE_THRESHOLD);
  const hiddenRows  = rows.filter((r) => r.oracle_probability <  VISIBLE_THRESHOLD);
  const displayRows = showAll ? rows : visibleRows;

  const updatedAt = predictions[0]?.predicted_at
    ? new Date(predictions[0].predicted_at).toLocaleString("en-US", {
        month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
      })
    : null;

  // All bets across every market for the weekend summary card — use actual
  // virtual_bets presence, not current edge, so prices moving post-bet-placement
  // don't cause a bet to silently disappear from the display.
  const allWeekendBets = predictions
    .filter((p) => p.has_bet)
    .sort((a, b) => {
      const marketOrder: Partial<Record<MarketType, number>> = { race_winner: 0, pole: 1, podium: 2 };
      const mDiff = (marketOrder[a.market_type] ?? 9) - (marketOrder[b.market_type] ?? 9);
      return mDiff !== 0 ? mDiff : b.edge - a.edge;
    });

  // Bet counts per market tab
  const betCountByMarket: Partial<Record<MarketType, number>> = {};
  for (const p of predictions) {
    if (p.has_bet) betCountByMarket[p.market_type] = (betCountByMarket[p.market_type] ?? 0) + 1;
  }

  // Context-aware status label based on race date
  const raceDate = new Date(race.race_date_utc);
  const now = new Date();
  const daysUntilRace = Math.ceil((raceDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const isCompleted = race.status === "completed";
  const statusLabel =
    isCompleted            ? "COMPLETED · MODEL v0.4" :
    daysUntilRace <= 0    ? "RACE DAY · MODEL v0.4" :
    daysUntilRace === 1   ? "RACE TOMORROW · MODEL v0.4" :
                            `RACE IN ${daysUntilRace}D · MODEL v0.4`;

  // Reset showAll when switching markets
  const handleMarketChange = (m: MarketType) => {
    setMarket(m);
    setShowAll(false);
  };

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
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Title row */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 6 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em", margin: 0, color: "#FAFAFA" }}>
          {race.name}
        </h1>
        <div style={{ fontSize: 12, color: isCompleted ? "#52525B" : daysUntilRace <= 1 ? "#E8002D" : "#52525B", fontFamily: MONO }}>
          {statusLabel}
        </div>
      </div>

      {/* Subtitle */}
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 20 }}>
        Round {race.round} · {race.circuit} · Race{" "}
        {new Date(race.race_date_utc).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
        {updatedAt && ` · Model updated ${updatedAt}`}
      </div>

      {/* Weekend positions card */}
      {allWeekendBets.length > 0 && (
        <div style={{ background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 10, marginBottom: 24, overflow: "hidden" }}>
          {/* Card header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px", borderBottom: "1px solid rgba(16,185,129,0.15)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <BetBadge />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#FAFAFA" }}>
                Oracle's Weekend Positions
              </span>
            </div>
            <span style={{ fontSize: 12, color: "#52525B", fontFamily: MONO }}>
              {allWeekendBets.length} bet{allWeekendBets.length !== 1 ? "s" : ""} · edge ≥ 5%
            </span>
          </div>
          {/* Bet rows */}
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#52525B", fontWeight: 500, padding: "8px 18px", textAlign: "left", background: "rgba(0,0,0,0.2)" }}>Market</th>
                <th style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#52525B", fontWeight: 500, padding: "8px 18px", textAlign: "left", background: "rgba(0,0,0,0.2)" }}>Driver</th>
                <th style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#52525B", fontWeight: 500, padding: "8px 18px", textAlign: "right", background: "rgba(0,0,0,0.2)", width: 72 }}>Oracle</th>
                <th style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#52525B", fontWeight: 500, padding: "8px 18px", textAlign: "right", background: "rgba(0,0,0,0.2)", width: 72 }}>Kalshi</th>
                <th style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#52525B", fontWeight: 500, padding: "8px 18px", textAlign: "right", background: "rgba(0,0,0,0.2)", width: 80 }}>Edge</th>
              </tr>
            </thead>
            <tbody>
              {allWeekendBets.map((bet, i) => {
                const abbrev = abbrevFromTicker(bet.kalshi_ticker);
                const marketLabel = bet.market_type === "race_winner" ? "WIN" : bet.market_type === "podium" ? "PODIUM" : bet.market_type === "pole" ? "POLE" : "SPRINT";
                return (
                  <tr key={`${bet.kalshi_ticker}-${bet.market_type}`} style={{ borderTop: i > 0 ? "1px solid rgba(16,185,129,0.08)" : undefined }}>
                    <td style={{ padding: "11px 18px" }}>
                      <span style={{ fontSize: 10, fontWeight: 600, fontFamily: MONO, letterSpacing: "0.1em", color: "#34D399", background: "rgba(16,185,129,0.12)", padding: "3px 8px", borderRadius: 4 }}>
                        {marketLabel}
                      </span>
                    </td>
                    <td style={{ padding: "11px 18px" }}>
                      <span style={{ fontFamily: MONO, fontWeight: 700, color: "#FAFAFA", fontSize: 13, letterSpacing: "0.04em", marginRight: 8 }}>{abbrev}</span>
                      <span style={{ color: "#A1A1AA", fontSize: 13 }}>{bet.driver_name}</span>
                    </td>
                    <td style={{ padding: "11px 18px", fontFamily: MONO, fontSize: 12, color: "#FAFAFA", textAlign: "right" }}>
                      {(bet.oracle_probability * 100).toFixed(1)}%
                    </td>
                    <td style={{ padding: "11px 18px", fontFamily: MONO, fontSize: 12, color: "#71717A", textAlign: "right" }}>
                      {(bet.kalshi_mid_price * 100).toFixed(1)}%
                    </td>
                    <td style={{ padding: "11px 18px", textAlign: "right" }}>
                      <Edge valuePct={bet.edge * 100} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Market pill tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
        {MARKETS.map((m) => {
          const active = market === m.key;
          return (
            <button
              key={m.key}
              onClick={() => handleMarketChange(m.key)}
              style={{
                display: "flex", alignItems: "center", gap: 7,
                padding: "7px 14px",
                borderRadius: 999,
                fontSize: 13,
                fontWeight: 500,
                background: active ? "#E8002D" : "#18181B",
                color: active ? "#FFFFFF" : "#A1A1AA",
                border: active ? "1px solid transparent" : "1px solid #27272A",
                cursor: "pointer",
              }}
            >
              {m.label}
              {(betCountByMarket[m.key] ?? 0) > 0 && (
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  fontFamily: MONO,
                  background: active ? "rgba(255,255,255,0.25)" : "rgba(16,185,129,0.2)",
                  color: active ? "#fff" : "#34D399",
                  borderRadius: 999,
                  padding: "1px 6px",
                  lineHeight: "1.4",
                }}>
                  {betCountByMarket[m.key]}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {rows.length === 0 ? (
        <div style={{ background: "#0E0E10", border: "1px solid #1F1F23", borderRadius: 8, padding: "32px 20px", textAlign: "center", color: "#71717A", fontSize: 14 }}>
          No predictions yet for this market. Run the model after qualifying.
        </div>
      ) : (
        <>
          <SectionCard>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ ...headerCell, width: 48, textAlign: "center" }}>#</th>
                  <th style={headerCell}>Driver</th>
                  <th style={{ ...headerCell, width: 220 }}>Oracle vs Kalshi</th>
                  <th style={{ ...headerCell, width: 90, textAlign: "right" }}>Payout</th>
                  <th style={{ ...headerCell, width: 90, textAlign: "right" }}>Edge</th>
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, i) => {
                  const hasBet = row.has_bet;
                  const rowBg = hasBet ? "rgba(16,185,129,0.06)" : (i % 2 === 0 ? "#0A0A0A" : "#0C0C0E");
                  const abbrev = abbrevFromTicker(row.kalshi_ticker);
                  const showKalshi = row.kalshi_mid_price > 0 && row.kalshi_mid_price < 0.94;
                  const multiplier = hasBet && row.kalshi_mid_price > 0 ? (1 / row.kalshi_mid_price).toFixed(1) + "×" : null;
                  return (
                    <tr key={row.kalshi_ticker} style={{ background: rowBg, borderBottom: "1px solid #15151A" }}>
                      <td style={{ padding: "16px 20px", color: "#52525B", fontSize: 12, fontFamily: MONO, textAlign: "center", borderLeft: hasBet ? "2px solid #10B981" : "2px solid transparent" }}>
                        {String(i + 1).padStart(2, "0")}
                      </td>
                      <td style={{ padding: "14px 20px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <span style={{ fontFamily: MONO, fontWeight: 700, color: "#FAFAFA", fontSize: 13, letterSpacing: "0.04em" }}>
                            {abbrev}
                          </span>
                          <span style={{ color: "#A1A1AA", fontSize: 13 }}>{row.driver_name}</span>
                          {hasBet && <BetBadge amount={row.bet_size_dollars} />}
                        </div>
                      </td>
                      <td style={{ padding: "12px 20px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <ProbBar valuePct={row.oracle_probability * 100} accent={true} />
                          {showKalshi && <ProbBar valuePct={row.kalshi_mid_price * 100} accent={false} />}
                        </div>
                      </td>
                      <td style={{ padding: "16px 20px", textAlign: "right" }}>
                        {multiplier ? (
                          <span style={{ display: "inline-flex", alignItems: "center", padding: "3px 8px", borderRadius: 4, fontFamily: MONO, fontSize: 11, fontWeight: 600, background: "rgba(16,185,129,0.1)", color: "#34D399", border: "1px solid rgba(16,185,129,0.2)" }}>
                            {multiplier}
                          </span>
                        ) : (
                          <span style={{ fontFamily: MONO, fontSize: 13, color: "#27272A" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "16px 20px", textAlign: "right" }}>
                        <Edge valuePct={row.edge * 100} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Show more / collapse toggle */}
            {hiddenRows.length > 0 && (
              <button
                onClick={() => setShowAll((v) => !v)}
                style={{
                  width: "100%",
                  padding: "11px 20px",
                  background: "transparent",
                  border: "none",
                  borderTop: "1px solid #1F1F23",
                  color: "#52525B",
                  fontSize: 12,
                  cursor: "pointer",
                  textAlign: "center",
                  letterSpacing: "0.02em",
                }}
              >
                {showAll
                  ? `Hide ${hiddenRows.length} drivers with 0.0% probability`
                  : `Show ${hiddenRows.length} more drivers (all 0.0% Oracle probability)`}
              </button>
            )}
          </SectionCard>

          {/* Legend */}
          <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 14, fontSize: 12, color: "#71717A" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: "#E8002D", display: "inline-block" }} />
              Oracle probability
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: "#52525B", display: "inline-block" }} />
              Kalshi mid-price
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <BetBadge />
              Virtual bet placed (edge ≥ 5%)
            </div>
          </div>
        </>
      )}
    </div>
  );
}
