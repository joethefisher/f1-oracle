"use client";
import { useState } from "react";
import type { RacePredictionRow } from "@/lib/queries";
import type { MarketType, Race } from "@/lib/types";

const MARKETS: { key: MarketType; label: string }[] = [
  { key: "race_winner", label: "Race Winner" },
  { key: "podium",      label: "Podium" },
  { key: "pole",        label: "Pole Position" },
];

function abbrevFromTicker(ticker: string): string {
  return ticker.split("-").pop() ?? "";
}

function EdgeBadge({ edge }: { edge: number }) {
  if (Math.abs(edge) < 0.02) return <span className="text-zinc-600 text-xs">—</span>;
  const positive = edge > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${positive ? "text-emerald-400" : "text-red-400"}`}>
      {positive ? "▲" : "▼"} {Math.abs(edge * 100).toFixed(1)}%
    </span>
  );
}

function BetBadge({ edge }: { edge: number }) {
  if (edge < 0.05) return null;
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
      BET
    </span>
  );
}

function ProbBars({ oracle, kalshi }: { oracle: number; kalshi: number }) {
  const showKalshi = kalshi > 0 && kalshi < 0.94;
  return (
    <div className="flex flex-col gap-1 min-w-[100px]">
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(oracle * 100, 100)}%` }} />
        </div>
        <span className="text-xs text-white tabular-nums w-10">{(oracle * 100).toFixed(1)}%</span>
      </div>
      {showKalshi && (
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
            <div className="h-full bg-zinc-500 rounded-full" style={{ width: `${Math.min(kalshi * 100, 100)}%` }} />
          </div>
          <span className="text-xs text-zinc-500 tabular-nums w-10">{(kalshi * 100).toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}

interface Props {
  race: Race;
  predictions: RacePredictionRow[];
}

export default function RaceView({ race, predictions }: Props) {
  const [market, setMarket] = useState<MarketType>("race_winner");

  const rows = predictions
    .filter((p) => p.market_type === market)
    .sort((a, b) => b.oracle_probability - a.oracle_probability);

  const updatedAt = predictions[0]?.predicted_at
    ? new Date(predictions[0].predicted_at).toLocaleString("en-US", {
        month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
      })
    : null;

  const betsPlaced = rows.filter((r) => r.edge >= 0.05).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">{race.name}</h1>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-zinc-500 text-sm">Round {race.round} · {race.circuit}</span>
          {updatedAt && (
            <span className="text-zinc-600 text-xs">· Model updated {updatedAt}</span>
          )}
        </div>
      </div>

      {/* Market tabs */}
      <div className="flex gap-2">
        {MARKETS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMarket(m.key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              market === m.key
                ? "bg-red-500 text-white"
                : "bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8 text-center text-zinc-500 text-sm">
          No predictions yet for this market. Run the model after qualifying.
        </div>
      ) : (
        <>
          {/* Summary strip */}
          {betsPlaced > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-zinc-400">Oracle placed</span>
              <span className="font-semibold text-emerald-400">{betsPlaced} bet{betsPlaced > 1 ? "s" : ""}</span>
              <span className="text-zinc-400">on this market (edge ≥ 5%)</span>
            </div>
          )}

          {/* Predictions table */}
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-900 text-zinc-400 text-xs uppercase tracking-wide">
                  <th className="text-left px-4 py-3 w-8">#</th>
                  <th className="text-left px-4 py-3">Driver</th>
                  <th className="text-left px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-red-400">Oracle</span>
                      <span className="text-zinc-600 font-normal normal-case tracking-normal">vs Kalshi</span>
                    </div>
                  </th>
                  <th className="text-right px-4 py-3">Edge</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const abbrev = abbrevFromTicker(row.kalshi_ticker);
                  const hasBet = row.edge >= 0.05;
                  return (
                    <tr
                      key={i}
                      className={`border-t border-zinc-800 transition-colors ${
                        hasBet ? "bg-emerald-950/30 hover:bg-emerald-950/50" : "bg-zinc-950 hover:bg-zinc-900"
                      }`}
                    >
                      <td className="px-4 py-3 text-zinc-600 text-xs tabular-nums">{i + 1}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono font-bold text-white text-sm">{abbrev}</span>
                          <span className="text-zinc-400 text-xs">{row.driver_name}</span>
                          <BetBadge edge={row.edge} />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <ProbBars oracle={row.oracle_probability} kalshi={row.kalshi_mid_price} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <EdgeBadge edge={row.edge} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-5 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-1.5 rounded-full bg-red-500 inline-block" /> Oracle probability
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-1.5 rounded-full bg-zinc-500 inline-block" /> Kalshi mid-price
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">BET</span>
              Virtual bet placed (edge ≥ 5%)
            </span>
          </div>
        </>
      )}
    </div>
  );
}
