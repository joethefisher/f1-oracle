import type { PortfolioSnapshot, RaceRecord } from "./types";

export const MOCK_RACE_PREDICTIONS = [
  { driver_name: "Lando Norris",      oracle_probability: 0.42, kalshi_mid_price: 0.35, edge: 0.07 },
  { driver_name: "Max Verstappen",    oracle_probability: 0.28, kalshi_mid_price: 0.32, edge: -0.04 },
  { driver_name: "Charles Leclerc",   oracle_probability: 0.14, kalshi_mid_price: 0.12, edge: 0.02 },
  { driver_name: "Oscar Piastri",     oracle_probability: 0.07, kalshi_mid_price: 0.08, edge: -0.01 },
  { driver_name: "Carlos Sainz",      oracle_probability: 0.05, kalshi_mid_price: 0.06, edge: -0.01 },
  { driver_name: "George Russell",    oracle_probability: 0.02, kalshi_mid_price: 0.04, edge: -0.02 },
  { driver_name: "Lewis Hamilton",    oracle_probability: 0.01, kalshi_mid_price: 0.02, edge: -0.01 },
  { driver_name: "Fernando Alonso",   oracle_probability: 0.01, kalshi_mid_price: 0.01, edge: 0.00 },
];

export const MOCK_PORTFOLIO: PortfolioSnapshot[] = [
  { id: 1, race_id: 1, race_name: "Bahrain GP",      bankroll_after: 1000.00, return_pct: 0.00,  kalshi_baseline_value: 1000.00, snapshot_at: "2026-03-15" },
  { id: 2, race_id: 2, race_name: "Saudi Arabian GP", bankroll_after: 1087.50, return_pct: 8.75,  kalshi_baseline_value: 1023.00, snapshot_at: "2026-03-22" },
  { id: 3, race_id: 3, race_name: "Australian GP",   bankroll_after: 1043.20, return_pct: 4.32,  kalshi_baseline_value: 1031.00, snapshot_at: "2026-03-29" },
  { id: 4, race_id: 4, race_name: "Japanese GP",     bankroll_after: 1156.80, return_pct: 15.68, kalshi_baseline_value: 1048.00, snapshot_at: "2026-04-06" },
  { id: 5, race_id: 5, race_name: "Miami GP",        bankroll_after: 1212.40, return_pct: 21.24, kalshi_baseline_value: 1061.00, snapshot_at: "2026-05-04" },
];

export const MOCK_SEASON_RECORDS: RaceRecord[] = [
  {
    race: { id: 5, name: "Miami Grand Prix", circuit: "Miami", round: 5, season: 2026,
            race_date_utc: "2026-05-04", is_sprint_weekend: false, status: "completed" },
    bets: [
      { driver_name: "Lando Norris", market_type: "race_winner", oracle_probability: 0.42,
        kalshi_mid_price: 0.35, edge: 0.07, bet_size_dollars: 45.50, won: true, pnl: 84.93 },
      { driver_name: "Charles Leclerc", market_type: "podium", oracle_probability: 0.68,
        kalshi_mid_price: 0.55, edge: 0.13, bet_size_dollars: 38.20, won: true, pnl: 31.25 },
    ],
    total_pnl: 116.18, n_bets: 2, n_wins: 2,
  },
  {
    race: { id: 4, name: "Japanese Grand Prix", circuit: "Suzuka", round: 4, season: 2026,
            race_date_utc: "2026-04-06", is_sprint_weekend: false, status: "completed" },
    bets: [
      { driver_name: "Max Verstappen", market_type: "race_winner", oracle_probability: 0.38,
        kalshi_mid_price: 0.30, edge: 0.08, bet_size_dollars: 52.00, won: true, pnl: 121.33 },
      { driver_name: "Lando Norris", market_type: "podium", oracle_probability: 0.71,
        kalshi_mid_price: 0.62, edge: 0.09, bet_size_dollars: 30.00, won: false, pnl: -30.00 },
    ],
    total_pnl: 91.33, n_bets: 2, n_wins: 1,
  },
];
