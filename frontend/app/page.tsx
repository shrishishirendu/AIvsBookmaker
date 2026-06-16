export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <p className="text-sm uppercase tracking-widest text-emerald-400">
        FIFA World Cup 2026
      </p>
      <h1 className="mt-3 text-5xl font-black leading-tight">
        AI vs Bookmakers
      </h1>
      <p className="mt-2 text-2xl font-semibold text-neutral-400">
        The Disagreement Engine
      </p>

      <p className="mt-8 text-lg text-neutral-300">
        Five named AIs publicly disagree before every match,{" "}
        <span className="text-white">commit their picks cryptographically</span>{" "}
        before kickoff so nobody can claim we edited them — then get vindicated
        or humiliated by the result, with receipts.
      </p>

      <div className="mt-10 rounded-xl border border-neutral-800 bg-neutral-900/60 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
          Phase 0 — shipped
        </h2>
        <ul className="mt-3 space-y-1 text-neutral-300">
          <li>✅ Provider abstraction · 5 models stubbed to mock</li>
          <li>✅ Commit → Lock → Reveal lifecycle (DB-enforced lock)</li>
          <li>✅ Public verification of every prediction hash</li>
        </ul>
        <p className="mt-4 text-sm text-neutral-500">
          Try the trust product: visit{" "}
          <code className="rounded bg-neutral-800 px-1.5 py-0.5 text-emerald-300">
            /verify/1
          </code>{" "}
          after seeding + running a match on the backend.
        </p>
      </div>

      <div className="mt-8 flex gap-3">
        <a
          href="/admin"
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
        >
          Open the Content Studio →
        </a>
        <a
          href="/play"
          className="rounded-md border border-neutral-700 px-4 py-2 text-sm font-semibold hover:border-neutral-500"
        >
          Can YOU beat the AIs?
        </a>
        <a
          href="/leaderboard"
          className="rounded-md border border-neutral-700 px-4 py-2 text-sm font-semibold hover:border-neutral-500"
        >
          Leaderboard
        </a>
        <a
          href="/highlights"
          className="rounded-md border border-neutral-700 px-4 py-2 text-sm font-semibold hover:border-neutral-500"
        >
          Highlights
        </a>
      </div>

      <p className="mt-8 text-sm text-neutral-500">
        Phase 1 — the viral content engine: 6 share templates, the Contrarian
        Spotlight, the Bookmaker Challenge, and the Receipt, each rendered as a
        screenshot-able card with captions for LinkedIn, Facebook, X, and Instagram.
      </p>
    </main>
  );
}
