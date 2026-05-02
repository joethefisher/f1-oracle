"use client";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import type { PortfolioSnapshot } from "@/lib/types";

const ACCENT = "#E8002D";
const MONO = "var(--font-geist-mono), ui-monospace, monospace";

interface ChartPoint {
  race: string;
  Oracle: number;
  "Kalshi Avg": number;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  const oracle = payload.find((p) => p.name === "Oracle")?.value;
  const kalshi = payload.find((p) => p.name === "Kalshi Avg")?.value;
  return (
    <div style={{ background: "#131316", border: "1px solid #27272A", borderRadius: 6, padding: "10px 12px", fontFamily: MONO, fontSize: 11 }}>
      <div style={{ color: "#71717A", letterSpacing: "0.1em", marginBottom: 6, textTransform: "uppercase" }}>{label}</div>
      {oracle != null && (
        <div style={{ color: "#FAFAFA", marginBottom: 3 }}>Oracle&nbsp;&nbsp; ${oracle.toFixed(2)}</div>
      )}
      {kalshi != null && (
        <div style={{ color: "#71717A" }}>Kalshi&nbsp;&nbsp; ${kalshi.toFixed(2)}</div>
      )}
    </div>
  );
}

export default function PortfolioChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const chartData: ChartPoint[] = [
    { race: "Start", Oracle: 1000, "Kalshi Avg": 1000 },
    ...snapshots.map((s) => ({
      race: s.race_name.replace(" Grand Prix", " GP").replace("Grand Prix", "GP"),
      Oracle: Math.round(s.bankroll_after * 100) / 100,
      "Kalshi Avg": Math.round(s.kalshi_baseline_value * 100) / 100,
    })),
  ];

  const allValues = chartData.flatMap((d) => [d.Oracle, d["Kalshi Avg"]]);
  const yMin = Math.floor(Math.min(...allValues) / 50) * 50 - 20;
  const yMax = Math.ceil(Math.max(...allValues) / 50) * 50 + 20;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 24, bottom: 8, left: 10 }}>
        <defs>
          <linearGradient id="oracleFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACCENT} stopOpacity={0.18} />
            <stop offset="100%" stopColor={ACCENT} stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid
          strokeDasharray="2 4"
          stroke="#1F1F23"
          vertical={false}
        />

        <XAxis
          dataKey="race"
          tick={{ fill: "#71717A", fontSize: 11, fontFamily: MONO }}
          tickLine={false}
          axisLine={{ stroke: "#1F1F23" }}
        />

        <YAxis
          domain={[yMin, yMax]}
          tick={{ fill: "#52525B", fontSize: 11, fontFamily: MONO }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `$${v.toLocaleString()}`}
          width={64}
        />

        <Tooltip content={<CustomTooltip />} />

        {/* Gradient area under Oracle line */}
        <Area
          type="monotone"
          dataKey="Oracle"
          fill="url(#oracleFill)"
          stroke="none"
          fillOpacity={1}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />

        {/* Kalshi dashed line */}
        <Line
          type="monotone"
          dataKey="Kalshi Avg"
          stroke="#71717A"
          strokeWidth={1.5}
          strokeDasharray="5 4"
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />

        {/* Oracle line on top */}
        <Line
          type="monotone"
          dataKey="Oracle"
          stroke={ACCENT}
          strokeWidth={2}
          dot={{ fill: ACCENT, r: 2.5, strokeWidth: 2, stroke: "#100D0B" }}
          activeDot={{ r: 5, fill: ACCENT, stroke: "#100D0B", strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
