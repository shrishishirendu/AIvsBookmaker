"use client";

import { useCallback, useEffect, useState } from "react";
import {
  abs,
  ContentItem,
  generateContent,
  getContent,
  fetchRealResult,
  getAdminKey,
  ingestResult,
  listMatches,
  lockMatch,
  MatchSummary,
  PLATFORMS,
  publishMatch,
  revealMatch,
  runPredict,
  seedAll,
  setAdminKey,
} from "@/lib/api";

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function fmtShort(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "2-digit",
      month: "short",
    });
  } catch {
    return iso;
  }
}

export default function AdminPage() {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [scoreA, setScoreA] = useState(2);
  const [scoreB, setScoreB] = useState(1);
  const [keyInput, setKeyInput] = useState("");
  const [keySaved, setKeySaved] = useState(false);

  useEffect(() => {
    setKeyInput(getAdminKey());
  }, []);

  const refreshMatches = useCallback(async () => {
    try {
      setMatches(await listMatches());
    } catch (e) {
      setError(`Backend unreachable on :8000? (${e})`);
    }
  }, []);

  useEffect(() => {
    refreshMatches();
  }, [refreshMatches]);

  const loadContent = useCallback(async (id: number) => {
    setContent((await getContent(id)).content);
  }, []);

  async function run<T>(label: string, fn: () => Promise<T>, okMsg?: (r: T) => string) {
    setBusy(label);
    setError(null);
    setFlash(null);
    try {
      const r = await fn();
      await refreshMatches();
      if (okMsg) setFlash(okMsg(r));
    } catch (e) {
      setError(`${label} failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(null);
    }
  }

  const select = async (id: number) => {
    setSelected(id);
    setContent([]);
    setFlash(null);
    setError(null);
    await loadContent(id);
  };

  const sm = matches.find((m) => m.id === selected) ?? null;
  const status = sm?.status ?? "NS";
  const predicted = ["PREDICTED", "LOCKED", "REVEALED", "FINISHED"].includes(status);
  const locked = !!sm?.locked;
  const revealed = ["REVEALED", "FINISHED"].includes(status);
  const finished = status === "FINISHED";

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-sm uppercase tracking-widest text-emerald-400">Content Studio</p>
          <h1 className="mt-1 text-2xl font-black">Admin — run a match lifecycle</h1>
        </div>
        <a href="/" className="text-sm text-neutral-400 hover:text-white">← home</a>
      </div>

      {/* operator key — required to run lifecycle actions on the live API */}
      <div className="mt-4 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-amber-300/90">🔑 Operator key</span>
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="paste ADMIN_API_KEY"
            className="min-w-[200px] flex-1 rounded bg-neutral-800 px-3 py-1.5 text-sm"
          />
          <button
            onClick={() => {
              setAdminKey(keyInput.trim());
              setKeySaved(true);
              setTimeout(() => setKeySaved(false), 1500);
            }}
            className="rounded bg-amber-700 px-3 py-1.5 text-sm font-medium hover:bg-amber-600"
          >
            {keySaved ? "✓ saved" : "Save"}
          </button>
        </div>
        <p className="mt-1.5 text-xs text-neutral-500">
          Required for the lifecycle actions on the live API. Stored only in this browser;
          never sent to anyone but your own backend.
        </p>
      </div>

      <div className="mt-6 grid gap-8 lg:grid-cols-[380px_1fr]">
        {/* ───────── sticky control rail ───────── */}
        <div className="lg:sticky lg:top-6 lg:self-start space-y-4">
          <button
            onClick={() => run("seed", () => seedAll(), () => "✓ Seeded — pick a match")}
            className="w-full rounded-md bg-neutral-800 px-3 py-2 text-sm font-medium hover:bg-neutral-700"
          >
            {busy === "seed" ? "Seeding…" : "Seed data"}
          </button>

          {/* match picker */}
          <div className="rounded-lg border border-neutral-800">
            <div className="border-b border-neutral-800 px-3 py-2 text-xs uppercase tracking-wide text-neutral-500">
              Matches ({matches.length})
            </div>
            <div className="max-h-[34vh] overflow-auto">
              {matches.map((m) => (
                <button
                  key={m.id}
                  onClick={() => select(m.id)}
                  className={`flex w-full items-center justify-between border-b border-neutral-900 px-3 py-2 text-left text-sm ${
                    selected === m.id ? "bg-emerald-950/40" : "hover:bg-neutral-900"
                  }`}
                >
                  <span className="min-w-0 truncate">
                    <span className="text-neutral-500">{fmtShort(m.kickoff_utc)} · </span>
                    {m.team_a} v {m.team_b}
                  </span>
                  <StatusDot status={m.status} />
                </button>
              ))}
              {matches.length === 0 && (
                <p className="px-3 py-3 text-sm text-neutral-500">Click “Seed data”.</p>
              )}
            </div>
          </div>

          {/* lifecycle controls for the selected match */}
          {sm && (
            <div className="rounded-lg border border-neutral-800 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-bold">{sm.team_a} v {sm.team_b}</span>
                <StatusPill status={status} />
              </div>
              <div className="mt-1 text-xs text-neutral-500">
                {fmtDate(sm.kickoff_utc)} · {sm.stage}
                {sm.degraded && " · ⚠ degraded"}
              </div>

              <div className="mt-4 space-y-2">
                <Step n={1} label="Predict" hint="run 5 AIs + commit"
                  state={predicted ? "done" : locked ? "disabled" : "active"}
                  busy={busy === "predict"}
                  onClick={() => run("predict", () => runPredict(selected!),
                    (r: { competitors: string[]; degraded: boolean }) =>
                      `✓ Predicted — ${r.competitors.length} committed${r.degraded ? " (some degraded)" : ""}. Next: Lock.`)} />
                <Step n={2} label="Lock" hint="freeze picks"
                  state={locked ? "done" : predicted ? "active" : "disabled"}
                  busy={busy === "lock"}
                  onClick={() => run("lock", () => lockMatch(selected!), () => "✓ Locked. Next: Reveal.")} />
                <Step n={3} label="Reveal" hint="un-seal picks"
                  state={revealed ? "done" : locked ? "active" : "disabled"}
                  busy={busy === "reveal"}
                  onClick={() => run("reveal", () => revealMatch(selected!), () => "✓ Revealed. Next: set result.")} />

                <div className={`rounded-md border px-2 py-2 ${
                  finished ? "border-emerald-700 bg-emerald-950/30"
                  : predicted ? "border-neutral-700 bg-neutral-900"
                  : "border-neutral-800 opacity-50"}`}>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-neutral-400 w-20">{finished ? "✓ 4. Result" : "4. Result"}</span>
                    <ScoreInput value={scoreA} onChange={setScoreA} disabled={!predicted} />
                    <span className="text-neutral-500">–</span>
                    <ScoreInput value={scoreB} onChange={setScoreB} disabled={!predicted} />
                    <button disabled={!predicted || busy !== null}
                      onClick={() => run("result", () => ingestResult(selected!, scoreA, scoreB),
                        (r: { final: string }) => `✓ Result ${r.final} recorded — leaderboard updated.`)}
                      className="ml-auto rounded bg-neutral-800 px-3 py-1 text-xs hover:bg-neutral-700 disabled:opacity-40">
                      {busy === "result" ? "…" : "Set manually"}
                    </button>
                  </div>
                  <button disabled={!predicted || busy !== null}
                    onClick={() => run("fetch-result", () => fetchRealResult(selected!),
                      (r: { final: string }) => `✓ Real result ${r.final} fetched & scored.`)}
                    className="mt-2 w-full rounded bg-sky-800 px-3 py-1.5 text-xs font-medium hover:bg-sky-700 disabled:opacity-40">
                    {busy === "fetch-result" ? "Fetching…" : "⬇ Fetch real result from API-Football"}
                  </button>
                </div>

                <button disabled={!predicted || busy !== null}
                  onClick={() => run("generate", async () => {
                    const r = await generateContent(selected!, true);
                    await loadContent(selected!);
                    return r;
                  }, (r: { generated: unknown[] }) => `✓ Generated ${r.generated.length} cards →`)}
                  className="w-full rounded-md bg-emerald-600 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
                  {busy === "generate" ? "Generating…" : predicted ? "✨ 5. Generate content" : "✨ Generate — Predict first"}
                </button>

                <button disabled={!predicted || busy !== null}
                  onClick={() => run("publish", () => publishMatch(selected!),
                    (r: { posted: number; total: number; dry_run: boolean }) =>
                      `📣 Published ${r.posted}/${r.total} posts${r.dry_run ? " (DRY-RUN — logged, not live)" : " LIVE"}.`)}
                  className="w-full rounded-md bg-sky-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
                  {busy === "publish" ? "Publishing…" : "📣 6. Publish to socials"}
                </button>
                <p className="text-[11px] text-neutral-500">
                  Auto-fires on schedule via Celery. Dry-run is ON by default — posts are
                  logged, not sent, until real credentials are added &amp; PUBLISH_DRY_RUN=false.
                </p>
              </div>

              {flash && <div className="mt-3 rounded-md border border-emerald-900 bg-emerald-950/40 p-2 text-xs text-emerald-300">{flash}</div>}
              {error && <div className="mt-3 rounded-md border border-red-900 bg-red-950/40 p-2 text-xs text-red-300">⚠ {error}</div>}
            </div>
          )}
        </div>

        {/* ───────── scrolling content column ───────── */}
        <div>
          {!sm && <p className="text-sm text-neutral-500">Pick a match from the rail to begin.</p>}
          {sm && content.length === 0 && (
            <p className="text-sm text-neutral-500">
              No content yet — run <b>Predict</b> (and optionally a result), then <b>Generate content</b>.
            </p>
          )}
          <div className="grid gap-6 xl:grid-cols-2">
            {content.map((c) => <ContentCard key={c.template} item={c} />)}
          </div>
        </div>
      </div>
    </main>
  );
}

function StatusDot({ status }: { status: string }) {
  const tone = status === "FINISHED" ? "bg-emerald-500"
    : status === "NS" ? "bg-neutral-600" : "bg-sky-500";
  return <span className={`ml-2 h-2 w-2 flex-none rounded-full ${tone}`} title={status} />;
}

function StatusPill({ status }: { status: string }) {
  const labels: Record<string, string> = {
    NS: "not started", PREDICTED: "predicted", LOCKED: "locked",
    REVEALED: "revealed", FINISHED: "finished",
  };
  const tone = status === "FINISHED" ? "bg-emerald-950 text-emerald-400"
    : status === "NS" ? "bg-neutral-800 text-neutral-400" : "bg-sky-950 text-sky-400";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${tone}`}>{labels[status] ?? status}</span>;
}

type StepState = "done" | "active" | "disabled";
function Step({ n, label, hint, state, onClick, busy }: {
  n: number; label: string; hint: string; state: StepState; onClick: () => void; busy: boolean;
}) {
  const styles: Record<StepState, string> = {
    done: "border-emerald-700 bg-emerald-950/30 text-emerald-300",
    active: "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-500",
    disabled: "border-neutral-800 bg-neutral-900/40 text-neutral-600 cursor-not-allowed",
  };
  return (
    <button onClick={onClick} disabled={state === "disabled" || busy}
      className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${styles[state]}`}>
      <span className="font-semibold">{state === "done" ? "✓" : `${n}.`} {busy ? "…" : label}</span>
      <span className="text-xs opacity-70">{state === "done" ? "done" : hint}</span>
    </button>
  );
}

function ScoreInput({ value, onChange, disabled }: {
  value: number; onChange: (n: number) => void; disabled?: boolean;
}) {
  return (
    <input type="number" min={0} disabled={disabled} value={value}
      onChange={(e) => onChange(Math.max(0, parseInt(e.target.value || "0", 10)))}
      className="w-11 rounded bg-neutral-800 px-2 py-1 text-center text-sm disabled:opacity-40" />
  );
}

function ContentCard({ item }: { item: ContentItem }) {
  const [platform, setPlatform] = useState<string>("x");
  const [copied, setCopied] = useState(false);
  const png = abs(item.png_url);
  const html = abs(item.html_url);
  const caption = item.captions[platform] ?? "";

  const copy = async () => {
    await navigator.clipboard.writeText(caption);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">{item.title}</h3>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
          item.triggered ? "bg-emerald-950 text-emerald-400" : "bg-neutral-800 text-neutral-500"}`}>
          {item.triggered ? "TRIGGERED" : "not triggered"}
        </span>
      </div>
      <div className="overflow-hidden rounded-lg border border-neutral-800 bg-black">
        {png ? <img src={png} alt={item.title} className="w-full" />
          : html ? <iframe src={html} title={item.title} className="h-[420px] w-full" style={{ border: "none" }} />
          : <div className="p-6 text-sm text-neutral-500">No image</div>}
      </div>
      <div className="mt-3 flex gap-1">
        {PLATFORMS.map((p) => (
          <button key={p} onClick={() => setPlatform(p)}
            className={`rounded px-2 py-1 text-xs capitalize ${
              platform === p ? "bg-emerald-600 text-white" : "bg-neutral-800 text-neutral-400 hover:text-white"}`}>
            {p}
          </button>
        ))}
        <button onClick={copy} className="ml-auto rounded bg-neutral-800 px-2 py-1 text-xs hover:bg-neutral-700">
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap rounded-lg bg-neutral-950 p-3 text-sm text-neutral-300">
        {caption}
      </pre>
    </div>
  );
}
