// Shared header + tab nav shell for all three F1 Oracle pages
const F1_RED = "#E8002D";

const TweakContext = React.createContext({
  accent: F1_RED,
  bg: "#0A0A0A",
  density: "regular",
  mono: true,
  cardStyle: "bordered",
  showBet: true,
});

function useT() { return React.useContext(TweakContext); }

function densityScale(d) {
  if (d === "compact") return { rowY: 10, cellY: 10, gap: 10, headerY: 9 };
  if (d === "comfy")   return { rowY: 18, cellY: 18, gap: 16, headerY: 14 };
  return { rowY: 14, cellY: 14, gap: 12, headerY: 12 };
}

function cardStyleFor(s, bg) {
  if (s === "elevated") return {
    background: bg === "#0A0A0A" ? "#141417" : (bg === "#0F1012" ? "#181A1D" : "#1A1714"),
    border: "1px solid transparent",
    borderRadius: 10,
    boxShadow: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.45)",
  };
  if (s === "flat") return {
    background: "transparent",
    border: "1px solid #1F1F23",
    borderRadius: 6,
  };
  // bordered (default)
  return {
    background: "#0E0E10",
    border: "1px solid #1F1F23",
    borderRadius: 8,
  };
}

function Shell({ activeTab, children, onTabChange }) {
  const t = useT();
  const tabs = ["Race Weekend", "Season Record", "Portfolio"];
  return (
    <div style={{
      width: "100%",
      minHeight: "100%",
      background: t.bg,
      color: "#FAFAFA",
      fontFamily: "'Geist', system-ui, sans-serif",
      fontFeatureSettings: '"ss01", "cv01"',
    }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 32px 0" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontWeight: 800, fontSize: 26, color: t.accent, letterSpacing: "-0.02em" }}>F1</span>
            <span style={{ fontWeight: 600, fontSize: 26, color: "#FAFAFA", letterSpacing: "-0.02em" }}>Oracle</span>
          </div>
          <span style={{ color: "#52525B", fontSize: 13 }}>ML model vs the crowd</span>
        </div>
        <div style={{ display: "flex", gap: 28, marginTop: 28, borderBottom: "1px solid #1F1F23" }}>
          {tabs.map(tab => {
            const active = tab === activeTab;
            return (
              <div key={tab}
                onClick={() => onTabChange && onTabChange(tab)}
                style={{
                  padding: "12px 2px",
                  fontSize: 14,
                  fontWeight: active ? 500 : 400,
                  color: active ? "#FAFAFA" : "#A1A1AA",
                  borderBottom: active ? `2px solid ${t.accent}` : "2px solid transparent",
                  marginBottom: -1,
                  cursor: "pointer",
                }}>{tab}</div>
            );
          })}
        </div>
      </div>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 32px 48px" }}>
        {children}
      </div>
    </div>
  );
}

function StatCard({ label, value, valueColor = "#FAFAFA", sub, width }) {
  const t = useT();
  const cs = cardStyleFor(t.cardStyle, t.bg);
  const pad = t.density === "compact" ? "14px 16px" : t.density === "comfy" ? "22px 24px" : "18px 20px";
  return (
    <div style={{ ...cs, padding: pad, flex: width ? `0 0 ${width}` : 1, minWidth: 0 }}>
      <div style={{
        fontSize: 11,
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        color: "#71717A",
        fontWeight: 500,
      }}>{label}</div>
      <div style={{
        marginTop: 8,
        fontSize: 30,
        fontWeight: 600,
        color: valueColor,
        fontFamily: t.mono ? "'Geist Mono', ui-monospace, monospace" : "'Geist', sans-serif",
        fontVariantNumeric: "tabular-nums",
        letterSpacing: "-0.02em",
        lineHeight: 1.05,
      }}>{value}</div>
      {sub && <div style={{ marginTop: 6, fontSize: 12, color: "#71717A" }}>{sub}</div>}
    </div>
  );
}

function Pill({ children, active }) {
  const t = useT();
  return (
    <div style={{
      padding: "7px 14px",
      borderRadius: 999,
      fontSize: 13,
      fontWeight: 500,
      background: active ? t.accent : "#18181B",
      color: active ? "#FFFFFF" : "#A1A1AA",
      border: active ? "1px solid transparent" : "1px solid #27272A",
      cursor: "pointer",
    }}>{children}</div>
  );
}

function BetBadge() {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      padding: "2px 7px",
      fontSize: 10,
      fontWeight: 600,
      letterSpacing: "0.08em",
      borderRadius: 4,
      background: "rgba(16,185,129,0.15)",
      color: "#34D399",
      border: "1px solid rgba(16,185,129,0.35)",
      fontFamily: "'Geist Mono', ui-monospace, monospace",
    }}>BET</span>
  );
}

function MarketBadge({ children }) {
  return (
    <span style={{
      display: "inline-flex",
      padding: "2px 7px",
      fontSize: 10,
      fontWeight: 600,
      letterSpacing: "0.08em",
      borderRadius: 4,
      background: "#27272A",
      color: "#D4D4D8",
      fontFamily: "'Geist Mono', ui-monospace, monospace",
    }}>{children}</span>
  );
}

function ProbBar({ value, color, max = 50 }) {
  const t = useT();
  const pct = Math.min(100, (value / max) * 100);
  const isAccent = color === "ACCENT";
  const fill = isAccent ? t.accent : color;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 90, height: 6, background: "#1F1F23", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: fill, borderRadius: 999 }} />
      </div>
      <div style={{
        fontFamily: "'Geist Mono', ui-monospace, monospace",
        fontSize: 12,
        fontVariantNumeric: "tabular-nums",
        color: isAccent ? "#FAFAFA" : "#71717A",
        width: 44,
        textAlign: "right",
      }}>{value.toFixed(1)}%</div>
    </div>
  );
}

function Edge({ value }) {
  if (Math.abs(value) < 2) {
    return <span style={{ color: "#52525B", fontFamily: "'Geist Mono', monospace", fontSize: 12 }}>—</span>;
  }
  const positive = value > 0;
  return (
    <span style={{
      color: positive ? "#34D399" : "#F87171",
      fontFamily: "'Geist Mono', ui-monospace, monospace",
      fontSize: 12,
      fontWeight: 600,
      fontVariantNumeric: "tabular-nums",
    }}>{positive ? "▲" : "▼"} {Math.abs(value).toFixed(1)}%</span>
  );
}

function SectionCard({ children, style }) {
  const t = useT();
  const cs = cardStyleFor(t.cardStyle, t.bg);
  return <div style={{ ...cs, overflow: "hidden", ...style }}>{children}</div>;
}

Object.assign(window, {
  Shell, StatCard, Pill, BetBadge, MarketBadge, ProbBar, Edge, SectionCard,
  TweakContext, useT, densityScale, cardStyleFor, F1_RED,
});
