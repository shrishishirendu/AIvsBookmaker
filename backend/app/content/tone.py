"""tone(platform, facts) -> caption (BUILD_SPEC §7).

ONE formatter, four voices — not four generators. Same facts rendered for:
  * linkedin  — analytical, professional
  * facebook  — fan, conversational
  * x         — punchy, <= 280 chars (hard cap)
  * instagram — caption + hashtags

Every template's `facts` dict carries a `kind`; we branch on it.
"""
from __future__ import annotations

PLATFORMS = ["linkedin", "facebook", "x", "instagram"]
X_LIMIT = 280

_HASHTAGS = "#WorldCup2026 #AIvsBookmakers #FootballPredictions"


def _clamp_x(text: str) -> str:
    if len(text) <= X_LIMIT:
        return text
    return text[: X_LIMIT - 1].rstrip() + "…"


def tone(platform: str, facts: dict) -> str:
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform {platform!r}")
    kind = facts.get("kind")
    builder = _BUILDERS.get(kind)
    if builder is None:
        return ""
    caption = builder(platform, facts)
    return _clamp_x(caption) if platform == "x" else caption


# --- per-template voices ----------------------------------------------------

def _lineup(platform: str, f: dict) -> str:
    a, b, stage = f["team_a"], f["team_b"], f["stage"]
    n = len(f["picks"])
    if platform == "linkedin":
        lines = [f"{a} vs {b} ({stage}). {n} frontier AI models have locked their calls:"]
        for p in f["picks"]:
            lines.append(f"• {p['competitor']}: {p['team']} ({p['confidence']}%)")
        if f.get("house"):
            lines.append(f"The House: {f['house']['team']} ({f['house']['confidence']}%).")
        lines.append("Picks are hash-committed pre-kickoff. Who's right?")
        return "\n".join(lines)
    if platform == "facebook":
        return (f"⚽ {a} vs {b} is coming! Our 5 AIs have made their calls — and they "
                f"don't all agree. Tap in and tell us who you've got. 👇")
    if platform == "x":
        teams = {}
        for p in f["picks"]:
            teams[p["team"]] = teams.get(p["team"], 0) + 1
        split = ", ".join(f"{v}×{k}" for k, v in teams.items())
        return f"🤖 5 AIs call {a} v {b}: {split}. Picks committed & hashed. {_HASHTAGS}"
    # instagram
    return (f"{a} 🆚 {b} — {stage}\nFive AIs. One match. Zero agreement.\n"
            f"Swipe to see every pick (all hash-committed before kickoff 🔒)\n{_HASHTAGS}")


def _contrarian(platform: str, f: dict) -> str:
    d, team, maj, n = f["dissenter"], f["dissent_team"], f["majority_team"], f["majority_count"]
    if not d:
        return ""
    if platform == "linkedin":
        return (f"Consensus break: {n} of our AI models back {maj}, but {d} is alone on "
                f"{team}. Single-dissenter calls are where the real conviction shows. "
                f"Bookmark this one.")
    if platform == "facebook":
        return (f"🚨 {d} is going rogue! While everyone else likes {maj}, {d} is backing "
                f"{team}. Bold call or genius read? 👀")
    if platform == "x":
        return f"🚨 {d} is going rogue on {team}. The other {n} AIs all say {maj}. Receipts committed. {_HASHTAGS}"
    return (f"🚨 ROGUE ALERT 🚨\n{d} is the lone wolf on {team} while {n} models ride with "
            f"{maj}.\nHero or zero? Kickoff decides.\n{_HASHTAGS}")


def _bookmaker(platform: str, f: dict) -> str:
    team, ai, book, diff = f["outcome_team"], f["ai_pct"], f["book_pct"], f["diff_pp"]
    if platform == "linkedin":
        return (f"Market vs machine on {team}: bookmakers imply {book}% (margin removed), "
                f"the AI consensus sits at {ai}% — a {diff}pp gap. Someone is mispricing this.")
    if platform == "facebook":
        return (f"💰🤖 The bookies say {book}% on {team}. The AIs say {ai}%. That's a {diff}-point "
                f"disagreement — somebody's getting this wrong!")
    if platform == "x":
        return f"The bookies say {book}%. The AIs say {ai}%. Someone's wrong about {team}. ({diff}pp gap) {_HASHTAGS}"
    return (f"BOOKIES vs BOTS 💰🤖\n{team}\nHouse: {book}%\nAIs: {ai}%\n{diff}-point gap. "
            f"Someone's wrong.\n{_HASHTAGS}")


def _reckoning(platform: str, f: dict) -> str:
    rows = f["rows"]
    risers = [r for r in rows if r["rank_delta"] > 0]
    top = min(rows, key=lambda r: r["rank"]) if rows else None
    if platform == "linkedin":
        lead = top["competitor"] if top else "—"
        return (f"The standings moved. {lead} leads. "
                + "; ".join(f"{r['competitor']} {r['points_delta']:+d}" for r in rows[:6])
                + ". The machines are separating.")
    if platform == "facebook":
        return (f"📊 The table just shifted! {(risers[0]['competitor'] if risers else 'Nobody')} "
                f"made the biggest jump this round. Full standings below 👇")
    if platform == "x":
        deltas = " ".join(f"{r['competitor']}{r['points_delta']:+d}" for r in rows[:5])
        return f"📊 The Reckoning: {deltas} {_HASHTAGS}"
    return ("📊 THE RECKONING\nThe leaderboard moved after that result.\n"
            + "\n".join(f"{r['rank']}. {r['competitor']} ({r['points_delta']:+d})" for r in rows[:6])
            + f"\n{_HASHTAGS}")


def _vindication(platform: str, f: dict) -> str:
    hero, villain, final = f.get("hero"), f.get("villain"), f.get("final")
    if not hero:
        return ""
    if platform == "linkedin":
        return (f"Final {final}. Best call: {hero['competitor']} ({hero['pick']}, "
                f"{hero['points']} pts). Worst miss: {villain['competitor']} "
                f"({villain['pick']} at {villain['confidence']}% confidence). Receipts verified.")
    if platform == "facebook":
        return (f"🏆 {hero['competitor']} NAILED it ({hero['pick']})! Meanwhile "
                f"{villain['competitor']} 😬 ({villain['pick']}). Final: {final}.")
    if platform == "x":
        return (f"🏆 {hero['competitor']} called it ({hero['pick']}). "
                f"😬 {villain['competitor']} faceplanted ({villain['pick']}). FT {final}. {_HASHTAGS}")
    return (f"🏆 VINDICATION: {hero['competitor']} — {hero['pick']} ({hero['points']} pts)\n"
            f"😬 FACEPLANT: {villain['competitor']} — {villain['pick']}\nFinal {final}\n{_HASHTAGS}")


def _receipt(platform: str, f: dict) -> str:
    a, b = f["team_a"], f["team_b"]
    if not f["revealed"]:
        if platform == "linkedin":
            return (f"{a} vs {b}: every AI prediction is now hash-committed. The plaintext "
                    f"stays sealed until kickoff — then anyone can re-hash and verify. No edits possible.")
        if platform == "facebook":
            return f"🔒 Locked in! Every pick for {a} vs {b} is hash-committed. No take-backs!"
        if platform == "x":
            return f"🔒 {a} v {b}: all AI picks hash-committed pre-kickoff. Re-hash & verify after. No edits. {_HASHTAGS}"
        return f"🔒 SEALED\n{a} vs {b}\nEvery pick cryptographically committed.\nVerify after kickoff.\n{_HASHTAGS}"
    vc, total = f["verified_count"], f["total"]
    if platform == "linkedin":
        return (f"{a} vs {b}: {vc}/{total} predictions revealed and independently verified against "
                f"their pre-kickoff hashes. This is what accountable prediction looks like.")
    if platform == "facebook":
        return f"✅ Receipts! {vc}/{total} picks for {a} vs {b} match their pre-kickoff hashes exactly. Proof, not promises."
    if platform == "x":
        return f"✅ {vc}/{total} picks verified against their pre-kickoff hashes. {a} v {b}. The receipts are real. {_HASHTAGS}"
    return f"✅ VERIFIED\n{a} vs {b}\n{vc}/{total} picks match their committed hashes.\nReceipts don't lie.\n{_HASHTAGS}"


_BUILDERS = {
    "lineup": _lineup,
    "contrarian": _contrarian,
    "bookmaker": _bookmaker,
    "reckoning": _reckoning,
    "vindication": _vindication,
    "receipt": _receipt,
}
