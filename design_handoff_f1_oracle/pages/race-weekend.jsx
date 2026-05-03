function RaceWeekend() {
  const t = useT();
  const showBet = t.showBet;
  const drivers = [
    { rank: 1, abbr: "ANT", name: "Andrea Kimi Antonelli", oracle: 46.8, kalshi: 39.0, bet: true },
    { rank: 2, abbr: "NOR", name: "Lando Norris",          oracle: 22.1, kalshi: 28.0, bet: false },
    { rank: 3, abbr: "VER", name: "Max Verstappen",        oracle: 18.4, kalshi: 19.0, bet: false },
    { rank: 4, abbr: "LEC", name: "Charles Leclerc",       oracle:  6.2, kalshi:  7.0, bet: false },
    { rank: 5, abbr: "PIA", name: "Oscar Piastri",         oracle:  4.1, kalshi:  4.0, bet: false },
    { rank: 6, abbr: "RUS", name: "George Russell",        oracle:  1.3, kalshi:  1.5, bet: false },
    { rank: 7, abbr: "HAM", name: "Lewis Hamilton",        oracle:  0.7, kalshi:  0.9, bet: false },
    { rank: 8, abbr: "SAI", name: "Carlos Sainz",          oracle:  0.4, kalshi:  0.6, bet: false },
  ];

  const headerCellStyle = {
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
    <Shell activeTab="Race Weekend">
      {/* Title */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 6 }}>
        <h1 style={{
          fontSize: 32,
          fontWeight: 600,
          letterSpacing: "-0.025em",
          margin: 0,
          color: "#FAFAFA",
        }}>Miami Grand Prix 2026</h1>
        <div style={{
          fontSize: 12,
          color: "#52525B",
          fontFamily: "'Geist Mono', ui-monospace, monospace",
        }}>LIVE · MODEL v0.4.2</div>
      </div>
      <div style={{ fontSize: 13, color: "#71717A", marginBottom: 18 }}>
        Round 4 · Miami International Autodrome · Model updated May 2, 9:14 PM
      </div>

      {/* Bet summary strip */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        background: "rgba(16,185,129,0.06)",
        border: "1px solid rgba(16,185,129,0.25)",
        borderRadius: 8,
        marginBottom: 22,
      }}>
        <BetBadge />
        <span style={{ fontSize: 13, color: "#D4D4D8" }}>
          Oracle placed <span style={{ color: "#FAFAFA", fontWeight: 500 }}>3 bets</span> on this market — total stake <span style={{ fontFamily: "'Geist Mono', monospace", color: "#FAFAFA" }}>$73.50</span> (edge ≥ 5%)
        </span>
      </div>

      {/* Market tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
        <Pill active>Race Winner</Pill>
        <Pill>Podium</Pill>
        <Pill>Pole Position</Pill>
      </div>

      {/* Predictions table */}
      <SectionCard>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ ...headerCellStyle, width: 48, textAlign: "center" }}>#</th>
              <th style={headerCellStyle}>Driver</th>
              <th style={{ ...headerCellStyle, width: 220 }}>Oracle vs Kalshi</th>
              <th style={{ ...headerCellStyle, width: 110, textAlign: "right" }}>Edge</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d, i) => {
              const rowBg = (showBet && d.bet) ? "rgba(16,185,129,0.06)" : (i % 2 === 0 ? "#0A0A0A" : "#0C0C0E");
              const leftBorder = (showBet && d.bet) ? "2px solid #10B981" : "2px solid transparent";
              return (
                <tr key={d.abbr} style={{ background: rowBg, borderBottom: "1px solid #15151A" }}>
                  <td style={{
                    padding: "16px 20px",
                    color: "#52525B",
                    fontSize: 12,
                    fontFamily: "'Geist Mono', monospace",
                    textAlign: "center",
                    borderLeft: leftBorder,
                  }}>{String(d.rank).padStart(2, "0")}</td>
                  <td style={{ padding: "14px 20px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{
                        fontFamily: "'Geist Mono', monospace",
                        fontWeight: 700,
                        color: "#FAFAFA",
                        fontSize: 13,
                        letterSpacing: "0.04em",
                      }}>{d.abbr}</span>
                      <span style={{ color: "#A1A1AA", fontSize: 13 }}>{d.name}</span>
                      {showBet && d.bet && <BetBadge />}
                    </div>
                  </td>
                  <td style={{ padding: "12px 20px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <ProbBar value={d.oracle} color="ACCENT" />
                      <ProbBar value={d.kalshi} color="#52525B" />
                    </div>
                  </td>
                  <td style={{ padding: "16px 20px", textAlign: "right" }}>
                    <Edge value={d.oracle - d.kalshi} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </SectionCard>

      {/* Legend */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 22,
        marginTop: 14,
        fontSize: 12,
        color: "#71717A",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: "#E8002D", display: "inline-block" }} />
          Oracle probability
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: "#52525B", display: "inline-block" }} />
          Kalshi mid-price
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <BetBadge />
          Virtual bet placed (edge ≥ 5%)
        </div>
      </div>
    </Shell>
  );
}

window.RaceWeekend = RaceWeekend;
