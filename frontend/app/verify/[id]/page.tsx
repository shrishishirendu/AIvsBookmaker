import { fetchVerify } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function VerifyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let data;
  let error: string | null = null;
  try {
    data = await fetchVerify(id);
  } catch (e) {
    error = e instanceof Error ? e.message : "unknown error";
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <p className="text-sm uppercase tracking-widest text-emerald-400">
        The Receipt
      </p>
      <h1 className="mt-2 text-3xl font-black">Prediction #{id}</h1>

      {error && (
        <div className="mt-8 rounded-lg border border-red-900 bg-red-950/40 p-5 text-red-300">
          Could not reach the backend ({error}). Start the API and seed a match
          first.
        </div>
      )}

      {data && (
        <div className="mt-8 space-y-6">
          <div
            className={`rounded-xl border p-5 ${
              data.match
                ? "border-emerald-800 bg-emerald-950/30"
                : "border-red-800 bg-red-950/30"
            }`}
          >
            <div className="text-2xl font-bold">
              {data.match ? "✅ Verified" : "❌ Hash mismatch"}
            </div>
            <p className="mt-1 text-neutral-400">
              {data.match
                ? "The revealed plaintext re-hashes to the committed hash. Untampered."
                : "The plaintext does not match the published hash."}
            </p>
          </div>

          <Field label="Competitor" value={data.competitor} />
          <Field
            label="Commit hash (published pre-kickoff)"
            value={data.commit_hash}
            mono
          />
          <Field label="Committed at" value={data.committed_at} />
          <Field label="Revealed" value={String(data.revealed)} />

          {data.prediction ? (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
              <div className="text-sm uppercase tracking-wide text-neutral-400">
                Revealed pick
              </div>
              <div className="mt-2 text-xl font-semibold">
                {data.prediction.winner} · {data.prediction.score_a}-
                {data.prediction.score_b} ·{" "}
                {(data.prediction.win_probability * 100).toFixed(0)}%
              </div>
              <p className="mt-2 italic text-neutral-300">
                “{data.prediction.reasoning}”
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 text-neutral-400">
              Plaintext is still sealed — it reveals after kickoff. Only the hash
              is public for now.
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-neutral-500">
        {label}
      </div>
      <div className={`mt-1 break-all ${mono ? "font-mono text-sm" : ""}`}>
        {value}
      </div>
    </div>
  );
}
