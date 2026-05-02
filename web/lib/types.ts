export type MarketType = "race_winner" | "podium" | "pole" | "sprint";

export interface Race {
  id: number;
  name: string;
  circuit: string;
  round: number;
  season: number;
  race_date_utc: string;
  is_sprint_weekend: boolean;
  status: "upcoming" | "active" | "completed";
}

export interface Prediction {
  id: number;
  market_id: number;
  oracle_probability: number;
  kalshi_mid_price: number;
  edge: number;
  predicted_at: string;
  model_version: string;
  driver_name: string;
  market_type: MarketType;
  kalshi_ticker: string;
}

export interface VirtualBet {
  id: number;
  prediction_id: number;
  bet_size_dollars: number;
  kelly_fraction: number;
  bankroll_at_time: number;
  placed_at: string;
}

export interface Outcome {
  market_id: number;
  winning_side: "yes" | "no";
  settled_at: string;
}

export interface PortfolioSnapshot {
  id: number;
  race_id: number;
  race_name: string;
  bankroll_after: number;
  return_pct: number;
  kalshi_baseline_value: number;
  snapshot_at: string;
}

export interface RaceRecord {
  race: Race;
  bets: Array<{
    driver_name: string;
    market_type: MarketType;
    oracle_probability: number;
    kalshi_mid_price: number;
    edge: number;
    bet_size_dollars: number;
    won: boolean;
    pnl: number;
  }>;
  total_pnl: number;
  n_bets: number;
  n_wins: number;
}
