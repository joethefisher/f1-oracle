"""
Pure formatters for the race-weekend Telegram notifications.

Plain-data-in, string-out — no DB or network — so they're trivially testable.
The orchestrator queries the DB, calls these, and hands the text to notify.send.
"""

STARTING_BANKROLL = 1000.0


def format_bets_placed(race_name: str, bets: list[dict], bankroll: float) -> str:
    """🏁 What the bot just bet.

    bets: [{market_type, driver, oracle_prob, kalshi_mid, edge, bet_size}]
    """
    if not bets:
        return f"🏁 {race_name} — model ran, no bets met the edge threshold."
    total = sum(b["bet_size"] for b in bets)
    pct = (total / bankroll * 100) if bankroll else 0.0
    lines = [
        f"🏁 {race_name} — bets placed",
        f"{len(bets)} bets, ${total:.2f} staked ({pct:.1f}% of ${bankroll:.0f})",
        "",
    ]
    for b in sorted(bets, key=lambda x: x["bet_size"], reverse=True):
        lines.append(
            f"• {b['market_type']} {b['driver']}: "
            f"oracle {b['oracle_prob']*100:.1f}% vs kalshi {b['kalshi_mid']*100:.1f}% "
            f"(edge {b['edge']*100:+.1f}%) — ${b['bet_size']:.2f}"
        )
    return "\n".join(lines)


def format_results(race_name: str, winner: str | None, bet_results: list[dict]) -> str:
    """🏆 Race result + how each bet resolved.

    bet_results: [{market_type, driver, won (bool), pnl, bet_size}]
    """
    lines = [f"🏆 {race_name} — results"]
    lines.append(f"Winner: {winner}" if winner else "Winner: (unknown)")
    if not bet_results:
        lines.append("No bets were placed this weekend.")
        return "\n".join(lines)
    lines.append("")
    wins = 0
    for b in sorted(bet_results, key=lambda x: x["pnl"], reverse=True):
        mark = "✅" if b["won"] else "❌"
        wins += 1 if b["won"] else 0
        lines.append(f"{mark} {b['market_type']} {b['driver']}: {b['pnl']:+.2f}")
    net = sum(b["pnl"] for b in bet_results)
    lines.append("")
    lines.append(f"Record: {wins}/{len(bet_results)} won — net {net:+.2f} this weekend")
    return "\n".join(lines)


def format_portfolio(snapshot: dict, starting: float = STARTING_BANKROLL) -> str:
    """💰 Portfolio standing vs the Kalshi-crowd baseline.

    snapshot: {bankroll_after, return_pct, kalshi_baseline_value}
    """
    bankroll = float(snapshot["bankroll_after"])
    ret = float(snapshot["return_pct"])
    baseline = snapshot.get("kalshi_baseline_value")
    lines = [
        "💰 Portfolio update",
        f"Bankroll: ${bankroll:.2f} ({ret:+.2f}% season)",
    ]
    if baseline is not None:
        baseline = float(baseline)
        baseline_ret = (baseline - starting) / starting * 100
        lines.append(f"Kalshi-crowd baseline: ${baseline:.2f} ({baseline_ret:+.2f}%)")
        diff = bankroll - baseline
        verb = "ahead of" if diff >= 0 else "behind"
        lines.append(f"Oracle is {verb} the crowd by ${abs(diff):.2f} ({ret - baseline_ret:+.2f} pts)")
    return "\n".join(lines)
