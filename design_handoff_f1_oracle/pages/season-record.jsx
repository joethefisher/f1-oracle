function SeasonRecord() {
  const races = [
    {
      round: "R4", name: "Miami Grand Prix", date: "May 3, 2026",
      wins: 6, total: 8, pnl: 58.20, expanded: true,
      bets: [
        { driver: "Antonelli",  market: "WIN",    oracle: 46.8, kalshi: 39.0, edge:  7.8, size: 24.50, result: "WIN",  pnl:  29.85 },
        { driver: "Norris",     market: "PODIUM", oracle: 64.2, kalshi: 58.0, edge:  6.2, size: 18.00, result: "WIN",  pnl:  12.94 },
        { driver: "Verstappen", market: "POLE",   oracle: 41.0, kalshi: 35.0, edge:  6.0, size: 16.00, result: "WIN",  pnl:  29.71 },
        { driver: "Leclerc",    market: "PODIUM", oracle: 38.5, kalshi: 31.0, edge:  7.5, size: 15.00, result: "LOSS", pnl: -15.00 },
      ],
    },
    { round: "R3", name: "Japanese Grand Prix",  date: "Apr 12, 2026", wins: 4, total: 7, pnl:  21.40, expanded: false },
    { round: "R2", name: "Saudi Arabian GP",     date: "Mar 22, 2026", wins: 5, total: 9, pnl:  44.10, expanded: false },
    { round: "R1", name: "Bahrain Grand Prix",   date: "Mar 8, 2026",  wins: 3, total: 6, pnl: -12.80, expanded: false },
  ];

  const headerCell = {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.14em",
    color: "#71717A",
    fontWeight: 500,
    padding: "10px 16px",
    background: "#0A0A0A",
    borderBottom: "1px solid #1F1F23",
    textAlign: "left",
  };

  return (
    <Shell activeTab="Season Record">
      <div style={{ marginBottom: 6 }}>
        <h1 style={{
          fontSize: 32,
          fontWeight: 600,
          letterSpacing: "-0.025em",
          margin: 0,
          color: "#FAFAFA",
        }}>Season Record</h1>
      </div>
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 22 }}>
        2026 season · 4 of 24 races settled
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
        <StatCard label="Bets" value="47" sub="across 4 races" />
        <StatCard label="Hit Rate" value="61%" sub="29 wins · 18 losses" />
        <StatCard label="Virtual P&L" value="+$110.90" valueColor="#34D399" sub="+11.09% on $1,000" />
      </div>

      {/* Accordion list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {races.map((r, i) => (
          <SectionCard key={r.round}>
            {/* Header row */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "60px 1fr 160px 80px 110px 24px",
              alignItems: "center",
              padding: "16px 20px",
              background: r.expanded ? "#131316" : "#0E0E10",
              cursor: "pointer",
              gap: 12,
            }}>
              <span style={{
                fontFamily: "'Geist Mono', monospace",
                color: "#52525B",
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: "0.04em",
              }}>{r.round}</span>
              <span style={{ color: "#FAFAFA", fontWeight: 500, fontSize: 15 }}>{r.name}</span>
              <span style={{ color: "#71717A", fontSize: 12 }}>{r.date}</span>
              <span style={{
                color: "#A1A1AA",
                fontSize: 13,
                fontFamily: "'Geist Mono', monospace",
              }}>{r.wins}/{r.total}</span>
              <span style={{
                color: r.pnl >= 0 ? "#34D399" : "#F87171",
                fontSize: 14,
                fontWeight: 600,
                fontFamily: "'Geist Mono', monospace",
                fontVariantNumeric: "tabular-nums",
                textAlign: "right",
              }}>{r.pnl >= 0 ? "+" : "−"}${Math.abs(r.pnl).toFixed(2)}</span>
              <span style={{
                color: "#52525B",
                fontSize: 14,
                transform: r.expanded ? "rotate(180deg)" : "none",
                transition: "transform 0.2s",
                textAlign: "center",
              }}>▾</span>
            </div>

            {/* Expanded detail */}
            {r.expanded && r.bets && (
              <div>
                <table style={{ width: "100%", borderCollapse: "collapse", background: "#08080A" }}>
                  <thead>
                    <tr>
                      <th style={headerCell}>Driver</th>
                      <th style={{ ...headerCell, width: 72 }}>Market</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Oracle</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Kalshi</th>
                      <th style={{ ...headerCell, width: 80, textAlign: "right" }}>Edge</th>
                      <th style={{ ...headerCell, width: 90, textAlign: "right" }}>Bet Size</th>
                      <th style={{ ...headerCell, width: 90 }}>Result</th>
                      <th style={{ ...headerCell, width: 100, textAlign: "right" }}>P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.bets.map((b, j) => (
                      <tr key={j} style={{ borderBottom: j === r.bets.length - 1 ? "none" : "1px solid #15151A" }}>
                        <td style={{ padding: "12px 16px", color: "#FAFAFA", fontSize: 13 }}>{b.driver}</td>
                        <td style={{ padding: "12px 16px" }}><MarketBadge>{b.market}</MarketBadge></td>
                        <td style={{ padding: "12px 16px", color: "#FAFAFA", fontFamily: "'Geist Mono', monospace", fontSize: 12, textAlign: "right" }}>{b.oracle.toFixed(1)}%</td>
                        <td style={{ padding: "12px 16px", color: "#71717A", fontFamily: "'Geist Mono', monospace", fontSize: 12, textAlign: "right" }}>{b.kalshi.toFixed(1)}%</td>
                        <td style={{ padding: "12px 16px", textAlign: "right" }}><Edge value={b.edge} /></td>
                        <td style={{ padding: "12px 16px", color: "#D4D4D8", fontFamily: "'Geist Mono', monospace", fontSize: 12, textAlign: "right" }}>${b.size.toFixed(2)}</td>
                        <td style={{ padding: "12px 16px" }}>
                          <span style={{
                            color: b.result === "WIN" ? "#34D399" : "#F87171",
                            fontSize: 12,
                            fontWeight: 600,
                            fontFamily: "'Geist Mono', monospace",
                            letterSpacing: "0.04em",
                          }}>{b.result} {b.result === "WIN" ? "✓" : "✗"}</span>
                        </td>
                        <td style={{
                          padding: "12px 16px",
                          color: b.pnl >= 0 ? "#34D399" : "#F87171",
                          fontFamily: "'Geist Mono', monospace",
                          fontSize: 12,
                          fontWeight: 600,
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                        }}>{b.pnl >= 0 ? "+" : "−"}${Math.abs(b.pnl).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        ))}
      </div>
    </Shell>
  );
}

window.SeasonRecord = SeasonRecord;
