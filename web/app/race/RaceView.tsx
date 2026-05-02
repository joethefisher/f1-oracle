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

  const betsPlaced = rows.filter((r) => r.edge >= 0.05);

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
        <div style={{ fontSize: 12, color: "#52525B", fontFamily: MONO }}>
          LIVE · MODEL v0.4
        </div>
      </div>

      {/* Subtitle */}
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 20 }}>
        Round {race.round} · {race.circuit}
        {updatedAt && ` · Model updated ${updatedAt}`}
      </div>

      {/* Bet summary strip */}
      {betsPlaced.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: 8, marginBottom: 22 }}>
          <BetBadge />
          <span style={{ fontSize: 13, color: "#D4D4D8" }}>
            Oracle placed{" "}
            <span style={{ color: "#FAFAFA", fontWeight: 500 }}>{betsPlaced.length} bet{betsPlaced.length !== 1 ? "s" : ""}</span>
            {" "}on this market (edge ≥ 5%)
          </span>
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
                  <th style={{ ...headerCell, width: 110, textAlign: "right" }}>Edge</th>
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, i) => {
                  const hasBet = row.edge >= 0.05;
                  const rowBg = hasBet ? "rgba(16,185,129,0.06)" : (i % 2 === 0 ? "#0A0A0A" : "#0C0C0E");
                  const abbrev = abbrevFromTicker(row.kalshi_ticker);
                  const showKalshi = row.kalshi_mid_price > 0 && row.kalshi_mid_price < 0.94;
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
                          {hasBet && <BetBadge />}
                        </div>
                      </td>
                      <td style={{ padding: "12px 20px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <ProbBar valuePct={row.oracle_probability * 100} accent={true} />
                          {showKalshi && <ProbBar valuePct={row.kalshi_mid_price * 100} accent={false} />}
                        </div>
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
