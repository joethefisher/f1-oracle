"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import type { PortfolioSnapshot } from "@/lib/types";

interface ChartPoint {
  race: string;
  Oracle: number;
  "Kalshi Avg": number;
}

export default function PortfolioChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const chartData: ChartPoint[] = snapshots.map((s) => ({
    race: s.race_name.replace(" Grand Prix", " GP").replace(" Grand", ""),
    Oracle: Math.round(s.bankroll_after * 100) / 100,
    "Kalshi Avg": Math.round(s.kalshi_baseline_value * 100) / 100,
  }));

  return (
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
        <Legend wrapperStyle={{ paddingTop: 16, fontSize: 12, color: "#a1a1aa" }} />
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
  );
}
