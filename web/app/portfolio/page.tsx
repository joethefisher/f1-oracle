"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import { MOCK_PORTFOLIO } from "@/lib/mockData";

const STARTING = 1000.0;

export default function PortfolioPage() {
  const latest = MOCK_PORTFOLIO[MOCK_PORTFOLIO.length - 1];
  const returnPct = latest ? ((latest.bankroll_after - STARTING) / STARTING * 100) : 0;
  const baselineReturn = latest
    ? ((latest.kalshi_baseline_value - STARTING) / STARTING * 100)
    : 0;

  const chartData = MOCK_PORTFOLIO.map((s) => ({
    race: s.race_name.replace(" Grand Prix", " GP").replace(" Grand", ""),
    Oracle: Math.round(s.bankroll_after * 100) / 100,
    "Kalshi Avg": Math.round(s.kalshi_baseline_value * 100) / 100,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="col-span-2 sm:col-span-1 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Portfolio Value</div>
          <div className="text-3xl font-semibold text-white">
            ${latest?.bankroll_after.toFixed(2) ?? "1,000.00"}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Oracle Return</div>
          <div className={`text-2xl font-semibold ${returnPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {returnPct >= 0 ? "+" : ""}{returnPct.toFixed(2)}%
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Kalshi Avg Return</div>
          <div className={`text-2xl font-semibold ${baselineReturn >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {baselineReturn >= 0 ? "+" : ""}{baselineReturn.toFixed(2)}%
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Races Played</div>
          <div className="text-2xl font-semibold text-white">{MOCK_PORTFOLIO.length}</div>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-400 mb-4 uppercase tracking-wide">Portfolio vs Kalshi Average</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="race"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#3f3f46" }}
            />
            <YAxis
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v}`}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 6 }}
              labelStyle={{ color: "#a1a1aa" }}
              itemStyle={{ color: "#e4e4e7" }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`]}
            />
            <Legend
              wrapperStyle={{ paddingTop: 16, fontSize: 12, color: "#a1a1aa" }}
            />
            <Line
              type="monotone"
              dataKey="Oracle"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ fill: "#ef4444", r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="Kalshi Avg"
              stroke="#52525b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-lg border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Race</th>
              <th className="text-right px-4 py-3">Oracle Portfolio</th>
              <th className="text-right px-4 py-3">Oracle Return</th>
              <th className="text-right px-4 py-3">Kalshi Avg</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {[...MOCK_PORTFOLIO].reverse().map((snap) => (
              <tr key={snap.id} className="hover:bg-zinc-900/50 transition-colors">
                <td className="px-4 py-3 text-white">{snap.race_name}</td>
                <td className="px-4 py-3 text-right font-medium text-white">
                  ${snap.bankroll_after.toFixed(2)}
                </td>
                <td className={`px-4 py-3 text-right font-medium ${snap.return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {snap.return_pct >= 0 ? "+" : ""}{snap.return_pct.toFixed(2)}%
                </td>
                <td className="px-4 py-3 text-right text-zinc-400">
                  ${snap.kalshi_baseline_value.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-zinc-600">
        Oracle starts with $1,000 virtual bankroll. Kalshi Avg baseline spreads same dollar amount proportional to market prices.
        Data shown is mock/demo data. Connect Supabase to show live portfolio.
      </p>
    </div>
  );
}
