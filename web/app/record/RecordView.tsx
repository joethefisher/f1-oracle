"use client";
import { useState } from "react";
import type { RaceRecord, MarketType } from "@/lib/types";

const MARKET_LABELS: Record<MarketType, string> = {
  race_winner: "WIN",
  podium: "PODIUM",
  pole: "POLE",
  sprint: "SPRINT",
};

function PnlCell({ pnl }: { pnl: number }) {
  const pos = pnl >= 0;
  return (
    <span className={`font-medium tabular-nums ${pos ? "text-emerald-400" : "text-red-400"}`}>
      {pos ? "+" : ""}${pnl.toFixed(2)}
    </span>
  );
}

export default function RecordView({ records }: { records: RaceRecord[] }) {
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

  if (records.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 p-8 text-center text-zinc-500 text-sm">
        No settled bets yet. Season record will appear here after the first race.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Bets</div>
          <div className="text-2xl font-semibold text-white">{totalBets}</div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Hit Rate</div>
          <div className="text-2xl font-semibold text-white">
            {totalBets > 0 ? ((totalWins / totalBets) * 100).toFixed(0) : 0}%
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Virtual P&L</div>
          <div className={`text-2xl font-semibold ${totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {records.map((record) => {
          const isOpen = open.has(record.race.id);
          return (
            <div key={record.race.id} className="rounded-lg border border-zinc-800 overflow-hidden">
              <button
                onClick={() => toggle(record.race.id)}
                className="w-full flex items-center justify-between px-4 py-3 bg-zinc-900 hover:bg-zinc-800 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="text-zinc-500 text-sm w-12">R{record.race.round}</span>
                  <span className="font-medium text-white">{record.race.name}</span>
                  <span className="text-zinc-500 text-sm">
                    {record.race.race_date_utc?.slice(0, 10)}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-zinc-400">{record.n_wins}/{record.n_bets}</span>
                  <PnlCell pnl={record.total_pnl} />
                  <span className="text-zinc-600">{isOpen ? "▲" : "▼"}</span>
                </div>
              </button>

              {isOpen && record.bets.length > 0 && (
                <table className="w-full text-sm">
                  <thead className="bg-zinc-950 text-zinc-500 text-xs uppercase tracking-wide">
                    <tr>
                      <th className="text-left px-4 py-2">Driver</th>
                      <th className="text-left px-4 py-2">Market</th>
                      <th className="text-right px-4 py-2">Oracle</th>
                      <th className="text-right px-4 py-2">Kalshi</th>
                      <th className="text-right px-4 py-2">Edge</th>
                      <th className="text-right px-4 py-2">Bet</th>
                      <th className="text-right px-4 py-2">Result</th>
                      <th className="text-right px-4 py-2">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {record.bets.map((bet, i) => (
                      <tr key={i} className="hover:bg-zinc-900/50">
                        <td className="px-4 py-2.5 text-white">{bet.driver_name}</td>
                        <td className="px-4 py-2.5 text-zinc-400">{MARKET_LABELS[bet.market_type]}</td>
                        <td className="px-4 py-2.5 text-right text-white">
                          {(bet.oracle_probability * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2.5 text-right text-zinc-400">
                          {(bet.kalshi_mid_price * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2.5 text-right text-emerald-400">
                          +{(bet.edge * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">
                          ${bet.bet_size_dollars.toFixed(2)}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          {bet.won
                            ? <span className="text-emerald-400 font-medium">WIN ✓</span>
                            : <span className="text-red-400 font-medium">LOSS ✗</span>}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <PnlCell pnl={bet.pnl} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
