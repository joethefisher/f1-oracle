function Portfolio() {
  const t = useT();
  const ACCENT = t.accent;
  // Race-by-race portfolio history (most recent first in table; chart uses chronological)
  const history = [
    { race: "Miami GP",    round: "R4", oracle: 1142.33, kalshi: 1038.00, raceReturn:  5.82 },
    { race: "Japanese GP", round: "R3", oracle: 1079.45, kalshi: 1024.10, raceReturn:  2.10 },
    { race: "Saudi GP",    round: "R2", oracle: 1057.20, kalshi: 1014.80, raceReturn:  4.41 },
    { race: "Bahrain GP",  round: "R1", oracle: 1012.60, kalshi: 1008.30, raceReturn:  1.26 },
  ];

  // Chronological for chart: add starting $1000 point
  const chart = [
    { label: "Start", round: "—", oracle: 1000, kalshi: 1000 },
    { label: "Bahrain",  round: "R1", oracle: 1012.60, kalshi: 1008.30 },
    { label: "Saudi",    round: "R2", oracle: 1057.20, kalshi: 1014.80 },
    { label: "Japan",    round: "R3", oracle: 1079.45, kalshi: 1024.10 },
    { label: "Miami",    round: "R4", oracle: 1142.33, kalshi: 1038.00 },
  ];

  // Build SVG chart
  const W = 1036, H = 280, padL = 64, padR = 24, padT = 24, padB = 36;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const yMin = 980, yMax = 1180;
  const xFor = (i) => padL + (i / (chart.length - 1)) * innerW;
  const yFor = (v) => padT + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
  const oraclePath = chart.map((p, i) => `${i ? "L" : "M"}${xFor(i)},${yFor(p.oracle)}`).join(" ");
  const kalshiPath = chart.map((p, i) => `${i ? "L" : "M"}${xFor(i)},${yFor(p.kalshi)}`).join(" ");
  const oracleArea = `${oraclePath} L${xFor(chart.length - 1)},${padT + innerH} L${xFor(0)},${padT + innerH} Z`;

  const yTicks = [1000, 1050, 1100, 1150];

  const headerCell = {
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
    <Shell activeTab="Portfolio">
      <div>
        <h1 style={{
          fontSize: 32,
          fontWeight: 600,
          letterSpacing: "-0.025em",
          margin: 0,
          color: "#FAFAFA",
        }}>Portfolio</h1>
      </div>
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 22 }}>
        Virtual $1,000 starting bankroll · Kelly-fractional sizing · No real money
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
        <StatCard label="Portfolio Value" value="$1,142.33" sub="Started at $1,000.00" width="32%" />
        <StatCard label="Oracle Return" value="+14.23%" valueColor="#34D399" sub="vs Kalshi avg +3.80%" />
        <StatCard label="Kalshi Avg Return" value="+3.80%" sub="Crowd-weighted baseline" />
        <StatCard label="Races Played" value="4" sub="of 24 in 2026 season" />
      </div>

      {/* Chart card */}
      <SectionCard style={{ marginBottom: 22, padding: "20px 0 8px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "0 24px 12px" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#FAFAFA", marginBottom: 4 }}>Cumulative performance</div>
            <div style={{ fontSize: 12, color: "#71717A" }}>$ value across the 2026 season</div>
          </div>
          <div style={{ display: "flex", gap: 18, fontSize: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 14, height: 2, background: ACCENT, display: "inline-block" }} />
              <span style={{ color: "#D4D4D8" }}>Oracle</span>
              <span style={{ color: "#71717A", fontFamily: "'Geist Mono', monospace" }}>$1,142.33</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 14, height: 2, background: "#71717A", display: "inline-block", borderTop: "2px dashed #71717A" }} />
              <span style={{ color: "#D4D4D8" }}>Kalshi avg</span>
              <span style={{ color: "#71717A", fontFamily: "'Geist Mono', monospace" }}>$1,038.00</span>
            </div>
          </div>
        </div>

        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
          <defs>
            <linearGradient id="oracleFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={ACCENT} stopOpacity="0.18" />
              <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Y grid + labels */}
          {yTicks.map(t => (
            <g key={t}>
              <line x1={padL} x2={W - padR} y1={yFor(t)} y2={yFor(t)} stroke="#1F1F23" strokeDasharray={t === 1000 ? "0" : "2 4"} />
              <text x={padL - 12} y={yFor(t) + 4} fill="#52525B" fontSize="11" textAnchor="end" fontFamily="'Geist Mono', monospace">${t.toLocaleString()}</text>
            </g>
          ))}

          {/* X labels */}
          {chart.map((p, i) => (
            <text key={i} x={xFor(i)} y={H - 12} fill="#71717A" fontSize="11" textAnchor="middle">{p.label}</text>
          ))}

          {/* Oracle area */}
          <path d={oracleArea} fill="url(#oracleFill)" />

          {/* Kalshi dashed */}
          <path d={kalshiPath} fill="none" stroke="#71717A" strokeWidth="1.5" strokeDasharray="5 4" />

          {/* Oracle line */}
          <path d={oraclePath} fill="none" stroke={ACCENT} strokeWidth="2" />

          {/* Points on Oracle */}
          {chart.map((p, i) => (
            <circle key={i} cx={xFor(i)} cy={yFor(p.oracle)} r={i === chart.length - 1 ? 4 : 2.5} fill={ACCENT} stroke={t.bg} strokeWidth="2" />
          ))}

          {/* Tooltip on last point */}
          <g transform={`translate(${xFor(chart.length - 1) - 132}, ${yFor(chart[chart.length - 1].oracle) - 64})`}>
            <rect width="124" height="52" rx="6" fill="#131316" stroke="#27272A" />
            <text x="12" y="18" fill="#71717A" fontSize="10" fontFamily="'Geist Mono', monospace" letterSpacing="0.1em">MIAMI · R4</text>
            <text x="12" y="34" fill="#FAFAFA" fontSize="12" fontFamily="'Geist Mono', monospace">Oracle  $1,142.33</text>
            <text x="12" y="46" fill="#71717A" fontSize="11" fontFamily="'Geist Mono', monospace">Kalshi  $1,038.00</text>
          </g>
        </svg>
      </SectionCard>

      {/* History table */}
      <SectionCard>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={headerCell}>Race</th>
              <th style={{ ...headerCell, textAlign: "right" }}>Oracle Portfolio</th>
              <th style={{ ...headerCell, textAlign: "right" }}>Race Return</th>
              <th style={{ ...headerCell, textAlign: "right" }}>Kalshi Avg</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h, i) => (
              <tr key={h.round} style={{
                borderBottom: i === history.length - 1 ? "none" : "1px solid #15151A",
                background: i % 2 === 0 ? "#0A0A0A" : "#0C0C0E",
              }}>
                <td style={{ padding: "14px 20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontFamily: "'Geist Mono', monospace", color: "#52525B", fontSize: 12 }}>{h.round}</span>
                    <span style={{ color: "#FAFAFA", fontSize: 14 }}>{h.race}</span>
                  </div>
                </td>
                <td style={{ padding: "14px 20px", textAlign: "right", color: "#FAFAFA", fontFamily: "'Geist Mono', monospace", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                  ${h.oracle.toFixed(2)}
                </td>
                <td style={{ padding: "14px 20px", textAlign: "right" }}>
                  <span style={{
                    color: h.raceReturn >= 0 ? "#34D399" : "#F87171",
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: 13,
                    fontWeight: 600,
                  }}>{h.raceReturn >= 0 ? "+" : "−"}{Math.abs(h.raceReturn).toFixed(2)}%</span>
                </td>
                <td style={{ padding: "14px 20px", textAlign: "right", color: "#71717A", fontFamily: "'Geist Mono', monospace", fontSize: 13 }}>
                  ${h.kalshi.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    </Shell>
  );
}

window.Portfolio = Portfolio;
