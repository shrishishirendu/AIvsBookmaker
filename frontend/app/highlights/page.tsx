"use client";

import { useEffect, useState } from "react";
import { getHighlights, Highlights } from "@/lib/api";

export default function HighlightsPage() {
  const [data, setData] = useState<Highlights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHighlights().then(setData).catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-sm uppercase tracking-widest text-emerald-400">Tournament highlights</p>
      <h1 className="mt-1 text-3xl font-black">Upsets, heroes & faceplants</h1>

      {error && (
        <div className="mt-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Could not load highlights ({error}).
        </div>
      )}

      {data && (
        <div className="mt-8 space-y-10">
          {/* Upset Detector */}
          <section>
            <h2 className="text-lg font-bold">🚨 Upset Detector</h2>
            <p className="text-sm text-neutral-500">Matches the AI field mostly got wrong.</p>
            <div className="mt-3 space-y-2">
              {data.upsets.map((u) => (
                <div key={u.match_id} className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
                  <div>
                    <div className="font-semibold">{u.match} <span className="text-neutral-500">· {u.final}</span></div>
                    <div className="text-xs text-neutral-500">{u.stage}</div>
                  </div>
                  <div className="text-right text-sm">
                    <div className="font-bold text-red-400">{u.ai_correct}/{u.ai_total} AIs right</div>
                    <div className="text-xs text-neutral-500">
                      {u.nailed_by.length ? `nailed by ${u.nailed_by.join(", ")}` : "nobody called it"}
                    </div>
                  </div>
                </div>
              ))}
              {data.upsets.length === 0 && <Empty />}
            </div>
          </section>

          {/* Biggest wins / failures */}
          <div className="grid gap-8 md:grid-cols-2">
            <section>
              <h2 className="text-lg font-bold">🏆 Biggest Wins</h2>
              <p className="text-sm text-neutral-500">Best calls across the tournament.</p>
              <div className="mt-3 space-y-2">
                {data.best_calls.map((c, i) => (
                  <Row key={i} who={c.competitor} pick={c.pick} match={c.match}
                    final={c.final} right={`${c.points} pts`} tone="emerald" />
                ))}
                {data.best_calls.length === 0 && <Empty />}
              </div>
            </section>
            <section>
              <h2 className="text-lg font-bold">😬 Biggest Failures</h2>
              <p className="text-sm text-neutral-500">Most confident wrong calls.</p>
              <div className="mt-3 space-y-2">
                {data.worst_misses.map((c, i) => (
                  <Row key={i} who={c.competitor} pick={c.pick} match={c.match}
                    final={c.final} right={`${c.confidence}% sure`} tone="red" />
                ))}
                {data.worst_misses.length === 0 && <Empty />}
              </div>
            </section>
          </div>
        </div>
      )}
    </main>
  );
}

function Row({ who, pick, match, final, right, tone }: {
  who: string; pick: string; match: string; final: string; right: string; tone: "emerald" | "red";
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
      <div className="min-w-0">
        <div className="font-semibold">{who.replace(/^user:/, "@")}</div>
        <div className="truncate text-xs text-neutral-500">{pick} · {match} (FT {final})</div>
      </div>
      <span className={`ml-2 flex-none font-bold ${tone === "emerald" ? "text-emerald-400" : "text-red-400"}`}>{right}</span>
    </div>
  );
}

function Empty() {
  return <p className="text-sm text-neutral-600">Nothing yet — settle some matches first.</p>;
}
