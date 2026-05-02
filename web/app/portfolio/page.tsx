import { getPortfolioSnapshots } from "@/lib/queries";
import PortfolioChart from "./PortfolioChart";

export const revalidate = 300;

const STARTING = 1000.0;

export default async function PortfolioPage() {
  const snapshots = await getPortfolioSnapshots();

  const latest = snapshots[snapshots.length - 1];
  const returnPct = latest
    ? ((latest.bankroll_after - STARTING) / STARTING) * 100
    : 0;
  const baselineReturn = latest
    ? ((latest.kalshi_baseline_value - STARTING) / STARTING) * 100
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="col-span-2 sm:col-span-1 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Portfolio Value</div>
          <div className="text-3xl font-semibold text-white">
            ${latest?.bankroll_after.toFixed(2) ?? "1,000.00"}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Oracle Return</div>
          <div className={`text-2xl font-semibold ${returnPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {returnPct >= 0 ? "+" : ""}{returnPct.toFixed(2)}%
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Kalshi Avg Return</div>
          <div className={`text-2xl font-semibold ${baselineReturn >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {baselineReturn >= 0 ? "+" : ""}{baselineReturn.toFixed(2)}%
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-zinc-400 text-xs uppercase tracking-wide mb-1">Races Played</div>
          <div className="text-2xl font-semibold text-white">{snapshots.length}</div>
        </div>
      </div>

      {snapshots.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 p-8 text-center text-zinc-500 text-sm">
          Portfolio history will appear here after the first settled race.
        </div>
      ) : (
        <>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="text-sm font-medium text-zinc-400 mb-4 uppercase tracking-wide">
              Portfolio vs Kalshi Average
            </h2>
            <PortfolioChart snapshots={snapshots} />
          </div>

          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase tracking-wide">
                <tr>
                  <th className="text-left px-4 py-3">Race</th>
                  <th className="text-right px-4 py-3">Oracle Portfolio</th>
                  <th className="text-right px-4 py-3">Oracle Return</th>
                  <th className="text-right px-4 py-3">Kalshi Avg</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {[...snapshots].reverse().map((snap) => (
                  <tr key={snap.id} className="hover:bg-zinc-900/50 transition-colors">
                    <td className="px-4 py-3 text-white">{snap.race_name}</td>
                    <td className="px-4 py-3 text-right font-medium text-white">
                      ${snap.bankroll_after.toFixed(2)}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${snap.return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {snap.return_pct >= 0 ? "+" : ""}{snap.return_pct.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-400">
                      ${snap.kalshi_baseline_value.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <p className="text-xs text-zinc-600">
        Oracle starts with $1,000 virtual bankroll. Kalshi Avg baseline spreads the same dollar amount proportional to market prices.
      </p>
    </div>
  );
}
