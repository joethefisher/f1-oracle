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


def format_weekend_review(weekend: dict) -> str:
    """🔍 Favorites-faded post-mortem for the weekend.

    weekend: the dict returned by tools.review_weekend.load_weekend, i.e.
    {race_name, bet_time, by_market: {market_type: [row, ...]}}.

    Headlines the painful case (a favorite the model rated below market that
    then won) — that's the answer to "why didn't the bot bet the favorites."
    """
    race_name = weekend["race_name"]
    by_market = weekend.get("by_market", {})

    # Faded favorites that hit are the headline (e.g. "ANT won despite the
    # model rating ANT below the market").
    faded_hits, faded_misses = [], []
    for mtype, rows in by_market.items():
        for r in rows:
            if not r.get("is_favorite"):
                continue
            o, m = r.get("oracle"), r.get("market_mid")
            if o is None or m is None or o >= m:
                continue  # not faded
            (faded_hits if r["won"] else faded_misses).append((mtype, r))

    bets = [r for rows in by_market.values() for r in rows if r.get("bet_size", 0) > 0]
    wins = sum(1 for r in bets if r["won"])
    net = sum(r.get("pnl", 0.0) for r in bets)
    staked = sum(r["bet_size"] for r in bets)

    lines = [f"🔍 {race_name} — weekend review"]
    if bets:
        lines.append(f"Record: {wins}/{len(bets)} won · staked ${staked:.2f} · "
                     f"net {net:+.2f}")
    else:
        lines.append("No bets placed this weekend.")

    if faded_hits:
        lines.append("")
        lines.append(f"⚠️  {len(faded_hits)} faded favorite(s) hit — "
                     f"model rated them below the crowd and the crowd was right:")
        for mtype, r in sorted(faded_hits, key=lambda x: -(x[1]["market_mid"] or 0)):
            lines.append(
                f"• {mtype} {r['driver']}: oracle {r['oracle']*100:.1f}% vs "
                f"market {r['market_mid']*100:.1f}% (edge {(r['oracle']-r['market_mid'])*100:+.1f}%) "
                f"→ P{r['position']}"
            )
    elif faded_misses:
        lines.append("")
        lines.append("No faded favorites hit — value strategy held up.")

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
