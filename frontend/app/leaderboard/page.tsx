"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE, Badge, getPersonalities, Personalities } from "@/lib/api";

type Row = {
  rank: number;
  competitor: string;
  tier: "ai" | "bookmaker" | "public" | "user" | string;
  points: number;
  accuracy: number;
  exact_scores: number;
  matches: number;
};

const SCOPES = ["overall", "weekly", "knockout"] as const;

const TIER_STYLE: Record<string, string> = {
  ai: "bg-emerald-950 text-emerald-400",
  bookmaker: "bg-yellow-950 text-yellow-400",
  public: "bg-sky-950 text-sky-400",
  user: "bg-violet-950 text-violet-400",
};

export default function LeaderboardPage() {
  const [scope, setScope] = useState<string>("overall");
  const [rows, setRows] = useState<Row[]>([]);
  const [pers, setPers] = useState<Personalities | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (s: string) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/leaderboard?scope=${s}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`${res.status}`);
      setRows(await res.json());
    } catch (e) {
      setError(`Could not load leaderboard (${e}). Is the backend running and seeded?`);
      setRows([]);
    }
  }, []);

  useEffect(() => { load(scope); }, [scope, load]);
  useEffect(() => { getPersonalities().then(setPers).catch(() => setPers(null)); }, []);

  const badgesFor = (competitor: string): Badge[] => pers?.by_model[competitor] ?? [];

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-sm uppercase tracking-widest text-emerald-400">Three-way leaderboard</p>
      <h1 className="mt-1 text-3xl font-black">Can you beat the AIs and the bookies?</h1>

      <div className="mt-6 flex gap-2">
        {SCOPES.map((s) => (
          <button key={s} onClick={() => setScope(s)}
            className={`rounded-md px-3 py-1.5 text-sm capitalize ${
              scope === s ? "bg-emerald-600 text-white" : "bg-neutral-800 text-neutral-400 hover:text-white"}`}>
            {s}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">{error}</div>
      )}

      <div className="mt-6 overflow-hidden rounded-xl border border-neutral-800">
        <table className="w-full text-sm">
          <thead className="bg-neutral-900 text-neutral-400">
            <tr>
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Competitor</th>
              <th className="px-4 py-3 text-left">Tier</th>
              <th className="px-4 py-3 text-right">Points</th>
              <th className="px-4 py-3 text-right">Accuracy</th>
              <th className="px-4 py-3 text-right">Exact</th>
              <th className="px-4 py-3 text-right">Matches</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.competitor} className="border-t border-neutral-800">
                <td className="px-4 py-3 font-bold text-neutral-500">{r.rank}</td>
                <td className="px-4 py-3">
                  <div className="font-semibold">{r.competitor.replace(/^user:/, "@")}</div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {badgesFor(r.competitor).map((b) => (
                      <span key={b.key} title={b.label}
                        className="rounded-full bg-neutral-800 px-1.5 py-0.5 text-[11px] text-neutral-300">
                        {b.emoji} {b.label}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TIER_STYLE[r.tier] ?? "bg-neutral-800 text-neutral-400"}`}>
                    {r.tier}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-bold">{r.points}</td>
                <td className="px-4 py-3 text-right">{(r.accuracy * 100).toFixed(0)}%</td>
                <td className="px-4 py-3 text-right">{r.exact_scores}</td>
                <td className="px-4 py-3 text-right text-neutral-400">{r.matches}</td>
              </tr>
            ))}
            {rows.length === 0 && !error && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-neutral-500">
                No standings yet — settle a match (set a result) to populate the board.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* personality badge legend */}
      {pers && pers.badges.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
            Emergent personalities <span className="text-neutral-600">· derived nightly from the metrics</span>
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {pers.badges.map((b) => (
              <div key={b.key} className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
                <div className="font-semibold">{b.emoji} {b.label} — <span className="text-emerald-400">{b.model}</span></div>
                <div className="text-xs text-neutral-500">{b.desc} ({b.value})</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
