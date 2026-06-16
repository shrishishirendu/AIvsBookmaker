const COMPETITORS = [
  { name: "Claude", color: "#d97757" },
  { name: "ChatGPT", color: "#10a37f" },
  { name: "Gemini", color: "#4285f4" },
  { name: "Grok", color: "#e5e7eb" },
  { name: "DeepSeek", color: "#7c5cff" },
];

const STEPS = [
  {
    icon: "🔒",
    title: "Commit",
    body: "Before kickoff, each AI's pick is hashed (SHA-256) and published. The prediction is sealed — impossible to edit after the fact.",
  },
  {
    icon: "⏱️",
    title: "Lock",
    body: "At kickoff the picks freeze. Five AIs, on the record, publicly disagreeing — with the bookmakers as a sixth opinion.",
  },
  {
    icon: "✅",
    title: "Reveal & Verify",
    body: "After the whistle, picks are revealed and scored against the real result. Anyone can re-hash and prove nothing was changed.",
  },
];

export default function Home() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(800px 400px at 75% -10%, rgba(16,185,129,.20), transparent 60%)",
          }}
        />
        <div className="relative mx-auto max-w-4xl px-6 py-20 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-400">
            FIFA World Cup 2026
          </p>
          <h1 className="mt-4 text-5xl font-black leading-[1.05] sm:text-6xl">
            AI vs Bookmakers
          </h1>
          <p className="mt-3 text-2xl font-bold text-neutral-400">
            The Disagreement Engine
          </p>
          <p className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-neutral-300">
            Five of the world's top AIs predict every World Cup match — and they{" "}
            <span className="text-white">rarely agree</span>. Each locks its pick
            cryptographically <span className="text-white">before kickoff</span>,
            so nobody can claim we edited it. Then the result vindicates or
            humiliates them — <span className="text-emerald-400">with receipts</span>.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <a
              href="/play"
              className="rounded-lg bg-emerald-600 px-6 py-3 text-base font-bold text-white shadow-lg shadow-emerald-900/40 transition hover:bg-emerald-500"
            >
              Can YOU beat the AIs? →
            </a>
            <a
              href="/leaderboard"
              className="rounded-lg border border-neutral-700 px-6 py-3 text-base font-semibold transition hover:border-neutral-500"
            >
              Leaderboard
            </a>
            <a
              href="/highlights"
              className="rounded-lg border border-neutral-700 px-6 py-3 text-base font-semibold transition hover:border-neutral-500"
            >
              Highlights
            </a>
          </div>

          {/* Competitors */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-3">
            {COMPETITORS.map((c) => (
              <span
                key={c.name}
                className="flex items-center gap-2 rounded-full border border-neutral-800 bg-neutral-900/60 px-3 py-1.5 text-sm font-semibold"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: c.color }}
                />
                {c.name}
              </span>
            ))}
            <span className="flex items-center gap-2 rounded-full border border-yellow-800/60 bg-yellow-950/30 px-3 py-1.5 text-sm font-semibold text-yellow-400">
              🏠 The House
            </span>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-6 py-14">
        <h2 className="text-center text-sm font-semibold uppercase tracking-widest text-neutral-500">
          How it works
        </h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div
              key={s.title}
              className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
            >
              <div className="text-3xl">{s.icon}</div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-sm font-bold text-emerald-400">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-xl font-bold">{s.title}</h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Why it matters */}
      <section className="mx-auto max-w-3xl px-6 pb-20 text-center">
        <div className="rounded-2xl border border-neutral-800 bg-gradient-to-b from-neutral-900/60 to-neutral-950 p-8">
          <h2 className="text-2xl font-black">
            Predictions are cheap. Proof is the product.
          </h2>
          <p className="mt-3 text-neutral-300">
            Every pick is timestamped, hashed, and publicly verifiable. No
            hindsight edits, no cherry-picking. Watch the five AIs build
            reputations — and rivalries — across the tournament, and see whether
            anyone can out-predict the machines and the bookmakers.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <a
              href="/play"
              className="rounded-lg bg-emerald-600 px-6 py-3 font-bold text-white transition hover:bg-emerald-500"
            >
              Make your pick
            </a>
            <a
              href="/leaderboard"
              className="rounded-lg border border-neutral-700 px-6 py-3 font-semibold transition hover:border-neutral-500"
            >
              See the standings
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
