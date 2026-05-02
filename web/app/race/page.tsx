"use client";
import { useState } from "react";
import { MOCK_RACE_PREDICTIONS } from "@/lib/mockData";
import type { MarketType } from "@/lib/types";

const MARKETS: { key: MarketType; label: string }[] = [
  { key: "race_winner", label: "Race Winner" },
  { key: "podium",      label: "Podium" },
  { key: "pole",        label: "Pole Position" },
];

function EdgeBadge({ edge }: { edge: number }) {
  if (Math.abs(edge) < 0.02) return <span className="text-zinc-500">—</span>;
  const positive = edge > 0;
  return (
    <span className={`font-medium ${positive ? "text-emerald-400" : "text-red-400"}`}>
      {positive ? "+" : ""}{(edge * 100).toFixed(1)}%{positive ? " ↑" : " ↓"}
    </span>
  );
}

function ProbBar({ oracle, kalshi }: { oracle: number; kalshi: number }) {
  return (
    <div className="relative h-3 w-32 rounded bg-zinc-800 overflow-hidden">
      <div
        className="absolute inset-y-0 left-0 bg-zinc-600 rounded"
        style={{ width: `${kalshi * 100}%` }}
      />
      <div
        className="absolute inset-y-0 left-0 bg-red-500 rounded"
        style={{ width: `${oracle * 100}%`, opacity: 0.8 }}
      />
    </div>
  );
}

export default function RacePage() {
  const [market, setMarket] = useState<MarketType>("race_winner");

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-white">Miami Grand Prix</h1>
          <span className="text-zinc-500 text-sm">Round 5 · Miami International Autodrome</span>
        </div>
        <p className="text-zinc-500 text-sm mt-1">Post-qualifying · Model updated 2h ago</p>
      </div>

      <div className="flex gap-2">
        {MARKETS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMarket(m.key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              market === m.key
                ? "bg-red-500 text-white"
                : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Driver</th>
              <th className="text-left px-4 py-3">Probability</th>
              <th className="text-right px-4 py-3">Oracle</th>
              <th className="text-right px-4 py-3">Kalshi</th>
              <th className="text-right px-4 py-3">Edge</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {MOCK_RACE_PREDICTIONS.map((row, i) => (
              <tr key={i} className="hover:bg-zinc-900/50 transition-colors">
                <td className="px-4 py-3 font-medium text-white">{row.driver_name}</td>
                <td className="px-4 py-3">
                  <ProbBar oracle={row.oracle_probability} kalshi={row.kalshi_mid_price} />
                </td>
                <td className="px-4 py-3 text-right text-white">
                  {(row.oracle_probability * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right text-zinc-400">
                  {(row.kalshi_mid_price * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right">
                  <EdgeBadge edge={row.edge} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-500 opacity-80 inline-block" /> Oracle
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-zinc-600 inline-block" /> Kalshi
        </span>
        <span>Edge shown when ≥ 2%</span>
      </div>

      <p className="text-xs text-zinc-600 mt-2">
        Data shown is mock/demo data. Connect Supabase to show live Oracle predictions.
      </p>
    </div>
  );
}
