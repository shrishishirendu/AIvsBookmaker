"use client";

import { useEffect, useMemo, useState } from "react";
import { listMatches, MatchSummary, submitUserPrediction } from "@/lib/api";

export default function PlayPage() {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [matchId, setMatchId] = useState<number | null>(null);
  const [handle, setHandle] = useState("");
  const [winner, setWinner] = useState<"TEAM_A" | "DRAW" | "TEAM_B">("TEAM_A");
  const [scoreA, setScoreA] = useState(1);
  const [scoreB, setScoreB] = useState(0);
  const [conf, setConf] = useState(60);
  const [reasoning, setReasoning] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMatches().then((ms) => {
      const open = ms.filter((m) => !m.locked);
      setMatches(open);
      if (open[0]) setMatchId(open[0].id);
    }).catch((e) => setError(String(e)));
  }, []);

  const match = useMemo(
    () => matches.find((m) => m.id === matchId) ?? null,
    [matches, matchId],
  );

  async function submit() {
    if (!match || !handle.trim()) {
      setError("Pick a match and enter a handle.");
      return;
    }
    setBusy(true); setError(null); setResult(null);
    try {
      const r = await submitUserPrediction(match.id, {
        handle, winner, score_a: scoreA, score_b: scoreB,
        win_probability: conf / 100, reasoning: reasoning || "My call.",
      });
      setResult(`✓ Locked in as ${r.competitor} — commit ${r.commit_hash.slice(0, 16)}…`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <p className="text-sm uppercase tracking-widest text-emerald-400">Public predictions</p>
      <h1 className="mt-1 text-3xl font-black">Can YOU beat the AIs?</h1>
      <p className="mt-2 text-neutral-400">
        Lock your pick before kickoff — committed with the same hash mechanic as the AIs,
        then scored on the same leaderboard.
      </p>

      {error && <div className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">⚠ {error}</div>}
      {result && <div className="mt-4 rounded-lg border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-300">{result}</div>}

      <div className="mt-6 space-y-5 rounded-xl border border-neutral-800 bg-neutral-900/40 p-5">
        <Field label="Your handle">
          <input value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="e.g. messi_fan"
            className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm" />
        </Field>

        <Field label="Match (open for predictions)">
          <select value={matchId ?? ""} onChange={(e) => setMatchId(Number(e.target.value))}
            className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm">
            {matches.map((m) => (
              <option key={m.id} value={m.id}>{m.team_a} vs {m.team_b} — {m.stage}</option>
            ))}
          </select>
          {matches.length === 0 && <p className="mt-1 text-xs text-neutral-500">No open matches (all locked).</p>}
        </Field>

        {match && (
          <Field label="Who wins?">
            <div className="flex gap-2">
              {([["TEAM_A", match.team_a], ["DRAW", "Draw"], ["TEAM_B", match.team_b]] as const).map(([v, lbl]) => (
                <button key={v} onClick={() => setWinner(v)}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium ${
                    winner === v ? "bg-emerald-600 text-white" : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"}`}>
                  {lbl}
                </button>
              ))}
            </div>
          </Field>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Field label={match ? match.team_a : "Home"}>
            <input type="number" min={0} value={scoreA}
              onChange={(e) => setScoreA(Math.max(0, parseInt(e.target.value || "0", 10)))}
              className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm" />
          </Field>
          <Field label={match ? match.team_b : "Away"}>
            <input type="number" min={0} value={scoreB}
              onChange={(e) => setScoreB(Math.max(0, parseInt(e.target.value || "0", 10)))}
              className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm" />
          </Field>
        </div>

        <Field label={`Confidence: ${conf}%`}>
          <input type="range" min={20} max={95} value={conf}
            onChange={(e) => setConf(Number(e.target.value))} className="w-full" />
        </Field>

        <Field label="One-line reasoning">
          <input value={reasoning} onChange={(e) => setReasoning(e.target.value)} maxLength={280}
            placeholder="Why this result?" className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm" />
        </Field>

        <button onClick={submit} disabled={busy || !match || !handle.trim()}
          className="w-full rounded-md bg-emerald-600 px-4 py-3 font-bold text-white hover:bg-emerald-500 disabled:bg-neutral-800 disabled:text-neutral-500">
          {busy ? "Locking in…" : "🔒 Commit my prediction"}
        </button>
      </div>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs uppercase tracking-wide text-neutral-500">{label}</span>
      {children}
    </label>
  );
}
