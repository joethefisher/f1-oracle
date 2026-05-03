import { createServerClient } from "@/lib/supabase";
import type { Race, PortfolioSnapshot, RaceRecord, MarketType } from "@/lib/types";

export interface RacePredictionRow {
  driver_name: string;
  market_type: MarketType;
  kalshi_ticker: string;
  oracle_probability: number;
  kalshi_mid_price: number;
  edge: number;
  predicted_at: string;
}

export async function getActiveRace(): Promise<Race | null> {
  const supabase = await createServerClient();
  const { data } = await supabase
    .from("races")
    .select("*")
    .in("status", ["active", "upcoming"])
    .order("race_date_utc", { ascending: true })
    .limit(1)
    .single();
  return (data as Race) ?? null;
}

export async function getRacePredictions(
  raceId: number
): Promise<RacePredictionRow[]> {
  const supabase = await createServerClient();
  const { data } = await supabase
    .from("predictions")
    .select(`
      oracle_probability,
      kalshi_mid_price,
      edge,
      predicted_at,
      markets (
        driver_name,
        market_type,
        kalshi_ticker
      )
    `)
    .eq("markets.race_id", raceId)
    .eq("model_version", "v2")
    .order("oracle_probability", { ascending: false });

  if (!data) return [];

  return (data as unknown[])
    .map((row: unknown) => {
      const r = row as {
        oracle_probability: number;
        kalshi_mid_price: number;
        edge: number;
        predicted_at: string;
        markets: {
          driver_name: string | null;
          market_type: string;
          kalshi_ticker: string;
        } | null;
      };
      if (!r.markets) return null;
      return {
        driver_name: r.markets.driver_name ?? "",
        market_type: r.markets.market_type as MarketType,
        kalshi_ticker: r.markets.kalshi_ticker,
        oracle_probability: r.oracle_probability,
        kalshi_mid_price: r.kalshi_mid_price,
        edge: r.edge,
        predicted_at: r.predicted_at,
      };
    })
    .filter((r): r is RacePredictionRow => r !== null);
}

export async function getSeasonTotalRaces(season: number): Promise<number> {
  const supabase = await createServerClient();
  const { count } = await supabase
    .from("races")
    .select("*", { count: "exact", head: true })
    .eq("season", season);
  return count ?? 0;
}

export async function getSeasonRecords(season?: number): Promise<RaceRecord[]> {
  const supabase = await createServerClient();

  // First resolve which season to show: use the provided season, or find the latest
  let targetSeason = season;
  if (!targetSeason) {
    const { data: latestRace } = await supabase
      .from("races")
      .select("season")
      .eq("status", "completed")
      .order("season", { ascending: false })
      .limit(1)
      .single();
    if (!latestRace) return [];
    targetSeason = (latestRace as { season: number }).season;
  }

  const { data: races } = await supabase
    .from("races")
    .select("*")
    .eq("status", "completed")
    .eq("season", targetSeason)
    .order("round", { ascending: false });

  if (!races || races.length === 0) return [];

  const records: RaceRecord[] = [];

  for (const race of races as Race[]) {
    const { data: betsData } = await supabase
      .from("virtual_bets")
      .select(`
        bet_size_dollars,
        kelly_fraction,
        bankroll_at_time,
        predictions (
          oracle_probability,
          kalshi_mid_price,
          edge,
          markets (
            driver_name,
            market_type,
            race_id,
            outcomes ( winning_side )
          )
        )
      `)
      .eq("predictions.markets.race_id", race.id);

    if (!betsData) continue;

    type BetRow = {
      bet_size_dollars: number;
      predictions: {
        oracle_probability: number;
        kalshi_mid_price: number;
        edge: number;
        markets: {
          driver_name: string | null;
          market_type: string;
          race_id: number;
          outcomes: { winning_side: string }[] | null;
        } | null;
      } | null;
    };

    const bets = (betsData as unknown as BetRow[])
      .filter((b) => b.predictions?.markets?.race_id === race.id)
      .map((b) => {
        const pred = b.predictions!;
        const market = pred.markets!;
        const won = market.outcomes?.[0]?.winning_side === "yes";
        const pnl = won
          ? b.bet_size_dollars * (1 / pred.kalshi_mid_price - 1)
          : -b.bet_size_dollars;
        return {
          driver_name: market.driver_name ?? "",
          market_type: market.market_type as MarketType,
          oracle_probability: pred.oracle_probability,
          kalshi_mid_price: pred.kalshi_mid_price,
          edge: pred.edge,
          bet_size_dollars: b.bet_size_dollars,
          won,
          pnl,
        };
      });

    const n_wins = bets.filter((b) => b.won).length;
    records.push({
      race,
      bets,
      total_pnl: bets.reduce((s, b) => s + b.pnl, 0),
      n_bets: bets.length,
      n_wins,
    });
  }

  return records;
}

export async function getPortfolioSnapshots(): Promise<PortfolioSnapshot[]> {
  const supabase = await createServerClient();
  const { data } = await supabase
    .from("portfolio_snapshots")
    .select(`
      id,
      race_id,
      bankroll_after,
      return_pct,
      kalshi_baseline_value,
      snapshot_at,
      races ( name )
    `)
    .order("snapshot_at", { ascending: true });

  if (!data) return [];

  return (data as unknown[]).map((row: unknown) => {
    const r = row as {
      id: number;
      race_id: number;
      bankroll_after: number;
      return_pct: number;
      kalshi_baseline_value: number;
      snapshot_at: string;
      races: { name: string } | null;
    };
    return {
      id: r.id,
      race_id: r.race_id,
      race_name: r.races?.name ?? "",
      bankroll_after: r.bankroll_after,
      return_pct: r.return_pct,
      kalshi_baseline_value: r.kalshi_baseline_value,
      snapshot_at: r.snapshot_at,
    };
  });
}
