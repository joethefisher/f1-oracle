import type { ReactNode, CSSProperties } from "react";

const MONO = "var(--font-geist-mono), ui-monospace, 'Cascadia Code', monospace";

export function StatCard({
  label,
  value,
  valueColor = "#FAFAFA",
  sub,
  style,
}: {
  label: string;
  value: string;
  valueColor?: string;
  sub?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        background: "#0E0E10",
        border: "1px solid #1F1F23",
        borderRadius: 8,
        padding: "18px 20px",
        ...style,
      }}
    >
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.12em", color: "#71717A", fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ marginTop: 8, fontSize: 30, fontWeight: 600, color: valueColor, fontFamily: MONO, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.02em", lineHeight: 1.05 }}>
        {value}
      </div>
      {sub && <div style={{ marginTop: 6, fontSize: 12, color: "#71717A" }}>{sub}</div>}
    </div>
  );
}

export function BetBadge() {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 7px", fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", borderRadius: 4, background: "rgba(16,185,129,0.15)", color: "#34D399", border: "1px solid rgba(16,185,129,0.35)", fontFamily: MONO }}>
      BET
    </span>
  );
}

export function MarketBadge({ children }: { children: ReactNode }) {
  return (
    <span style={{ display: "inline-flex", padding: "2px 7px", fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", borderRadius: 4, background: "#27272A", color: "#D4D4D8", fontFamily: MONO }}>
      {children}
    </span>
  );
}

export function SectionCard({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div style={{ background: "#0E0E10", border: "1px solid #1F1F23", borderRadius: 8, overflow: "hidden", ...style }}>
      {children}
    </div>
  );
}

export function Edge({ valuePct }: { valuePct: number }) {
  if (Math.abs(valuePct) < 2) {
    return <span style={{ color: "#52525B", fontFamily: MONO, fontSize: 12 }}>—</span>;
  }
  const positive = valuePct > 0;
  return (
    <span style={{ color: positive ? "#34D399" : "#F87171", fontFamily: MONO, fontSize: 12, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
      {positive ? "▲" : "▼"} {Math.abs(valuePct).toFixed(1)}%
    </span>
  );
}

export function ProbBar({ valuePct, accent }: { valuePct: number; accent: boolean }) {
  const fill = accent ? "#E8002D" : "#52525B";
  const pct = Math.min(100, (valuePct / 50) * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 90, height: 6, background: "#1F1F23", borderRadius: 999, overflow: "hidden", flexShrink: 0 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: fill, borderRadius: 999 }} />
      </div>
      <div style={{ fontFamily: MONO, fontSize: 12, fontVariantNumeric: "tabular-nums", color: accent ? "#FAFAFA" : "#71717A", width: 44, textAlign: "right" }}>
        {valuePct.toFixed(1)}%
      </div>
    </div>
  );
}
