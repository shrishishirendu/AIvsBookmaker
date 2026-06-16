// Single place the frontend talks to the backend.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type VerifyResponse = {
  prediction_id: number;
  match_id: number;
  competitor: string;
  commit_hash: string;
  committed_at: string;
  revealed: boolean;
  prediction: {
    winner: string;
    score_a: number;
    score_b: number;
    win_probability: number;
    reasoning: string;
  } | null;
  match: boolean;
};

export async function fetchVerify(id: string): Promise<VerifyResponse> {
  const res = await fetch(`${API_BASE}/verify/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`verify ${id} failed: ${res.status}`);
  }
  return res.json();
}

export type MatchSummary = {
  id: number;
  team_a: string;
  team_b: string;
  stage: string;
  kickoff_utc: string;
  status: string;
  locked: boolean;
  degraded: boolean;
};

export type ContentItem = {
  template: string;
  title: string;
  triggered: boolean;
  html_url: string | null;
  png_url: string | null;
  image_url: string | null;
  captions: Record<string, string>;
};

const PLATFORMS = ["linkedin", "facebook", "x", "instagram"] as const;
export type Platform = (typeof PLATFORMS)[number];
export { PLATFORMS };

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // surface FastAPI's `detail` message instead of a bare status code
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const abs = (path: string | null) =>
  path ? (path.startsWith("http") ? path : `${API_BASE}${path}`) : null;

export const listMatches = () =>
  fetch(`${API_BASE}/matches`, { cache: "no-store" }).then((r) =>
    json<MatchSummary[]>(r),
  );

export const getContent = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/content`, { cache: "no-store" }).then((r) =>
    json<{ match_id: number; content: ContentItem[] }>(r),
  );

export const generateContent = (id: number, renderPng = true) =>
  fetch(`${API_BASE}/matches/${id}/content?render_png=${renderPng}`, {
    method: "POST",
  }).then((r) => json<{ match_id: number; generated: ContentItem[] }>(r));

export const seedAll = () =>
  fetch(`${API_BASE}/seed`, { method: "POST" }).then((r) => json(r));

export type PredictResult = {
  match_id: number;
  competitors: string[];
  degraded: boolean;
};

export const runPredict = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/predict`, { method: "POST" }).then((r) =>
    json<PredictResult>(r),
  );

export const lockMatch = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/lock`, { method: "POST" }).then((r) =>
    json(r),
  );

export const revealMatch = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/reveal`, { method: "POST" }).then((r) =>
    json(r),
  );

export const ingestResult = (id: number, score_a: number, score_b: number) =>
  fetch(`${API_BASE}/matches/${id}/result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ score_a, score_b }),
  }).then((r) => json<{ match_id: number; final: string }>(r));

export const fetchRealResult = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/fetch-result`, { method: "POST" }).then((r) =>
    json<{ match_id: number; final: string }>(r),
  );

export type Badge = { key: string; label: string; emoji: string };
export type Personalities = {
  badges: (Badge & { model: string; value: string; desc: string })[];
  by_model: Record<string, Badge[]>;
  models: {
    model: string; matches: number; points: number; accuracy: number;
    variance: number; ko_points: number; upsets: number; miss_confidence: number;
  }[];
};

export const getPersonalities = () =>
  fetch(`${API_BASE}/personalities`, { cache: "no-store" }).then((r) =>
    json<Personalities>(r),
  );

export type Highlights = {
  upsets: { match_id: number; match: string; stage: string; final: string;
    ai_correct: number; ai_total: number; nailed_by: string[] }[];
  best_calls: { match_id: number; match: string; competitor: string; pick: string;
    final: string; points: number; confidence: number }[];
  worst_misses: { match_id: number; match: string; competitor: string; pick: string;
    final: string; points: number; confidence: number }[];
};

export const getHighlights = () =>
  fetch(`${API_BASE}/highlights`, { cache: "no-store" }).then((r) => json<Highlights>(r));

export const publishMatch = (id: number) =>
  fetch(`${API_BASE}/matches/${id}/publish`, { method: "POST" }).then((r) =>
    json<{ match_id: number; dry_run: boolean; posted: number; total: number }>(r),
  );

export const submitUserPrediction = (
  id: number,
  body: { handle: string; winner: string; score_a: number; score_b: number;
    win_probability: number; reasoning: string },
) =>
  fetch(`${API_BASE}/matches/${id}/user-prediction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => json<{ competitor: string; commit_hash: string }>(r));
