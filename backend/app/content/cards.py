"""Styled, screenshot-able cards as self-contained HTML (BUILD_SPEC §7).

We build styled markup and screenshot it (render.py) rather than hand-drawing
images in code — far faster to iterate and they look designed. Each card is a
full HTML document sized to its social dimensions with all CSS inlined, so it
renders identically whether opened in a browser or captured by Playwright.

`render_card(template, image_spec) -> html` is the single entry point.
"""
from __future__ import annotations

import html

BRAND = "#10b981"   # emerald
GOLD = "#f5b301"
RED = "#ef4444"
BG = "#0a0a0a"


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _avatar(initial: str, color: str, size: int = 64) -> str:
    fg = "#0a0a0a" if color in ("#e5e7eb", "#f5b301") else "#ffffff"
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{color};'
        f'color:{fg};display:flex;align-items:center;justify-content:center;'
        f'font-weight:800;font-size:{int(size*0.42)}px;flex:none;">{_esc(initial)}</div>'
    )


def _doc(width: int, height: int, eyebrow: str, title: str, body: str, top_align: bool = False) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:{width}px; height:{height}px; }}
  .card {{
    width:{width}px; height:{height}px; padding:72px 64px;
    background:
      radial-gradient(900px 500px at 80% -10%, rgba(16,185,129,.18), transparent 60%),
      linear-gradient(160deg, #111 0%, {BG} 70%);
    color:#fff; font-family:'Segoe UI',system-ui,-apple-system,Roboto,Arial,sans-serif;
    display:flex; flex-direction:column; position:relative; overflow:hidden;
  }}
  .eyebrow {{ color:{BRAND}; font-size:24px; font-weight:700; letter-spacing:.22em;
              text-transform:uppercase; }}
  .title {{ font-size:62px; font-weight:900; line-height:1.02; margin-top:14px; }}
  /* footer sits in normal flow at the bottom — never overlaps content */
  .footer {{ margin-top:28px; padding-top:20px; border-top:1px solid #1f1f23;
             display:flex; justify-content:space-between; align-items:center;
             color:#71717a; font-size:22px; font-weight:600; flex:none; }}
  .body {{ flex:1; min-height:0; display:flex; flex-direction:column;
           justify-content:{"flex-start" if top_align else "center"}; overflow:hidden; }}
</style></head><body>
  <div class="card">
    <div style="flex:none;"><div class="eyebrow">{_esc(eyebrow)}</div><div class="title">{title}</div></div>
    <div class="body">{body}</div>
    <div class="footer"><span>🔒 hash-committed pre-kickoff</span><span>The Disagreement Engine</span></div>
  </div>
</body></html>"""


def _confidence_bar(pct: int, color: str) -> str:
    return (
        f'<div style="height:12px;background:#27272a;border-radius:6px;overflow:hidden;width:220px;">'
        f'<div style="height:100%;width:{pct}%;background:{color};border-radius:6px;"></div></div>'
    )


# --- 1. Lineup Card ---------------------------------------------------------

def _lineup(spec: dict) -> str:
    rows = ""
    for p in spec["picks"]:
        rows += f"""
        <div style="display:flex;align-items:center;gap:20px;padding:14px 0;border-bottom:1px solid #1f1f23;">
          {_avatar(p['competitor'][0], p['color'], 50)}
          <div style="flex:1;min-width:0;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;">
              <span style="font-size:27px;font-weight:800;">{_esc(p['competitor'])}</span>
              <span style="font-size:27px;font-weight:800;color:{p['color']};white-space:nowrap;">{_esc(p['team'])} {_esc(p['score'])}</span>
            </div>
            <div style="display:flex;align-items:center;gap:14px;margin-top:7px;">
              {_confidence_bar(p['confidence'], p['color'])}
              <span style="color:#a1a1aa;font-size:20px;">{p['confidence']}%</span>
            </div>
            <div style="color:#d4d4d8;font-size:18px;line-height:1.3;margin-top:7px;font-style:italic;">“{_esc(p['reasoning'])}”</div>
          </div>
        </div>"""
    house = ""
    if spec.get("house"):
        h = spec["house"]
        house = f"""
        <div style="margin-top:20px;padding:20px 24px;border:2px solid {GOLD};border-radius:16px;
                    background:rgba(245,179,1,.08);display:flex;justify-content:space-between;align-items:center;gap:16px;">
          <div><div style="color:{GOLD};font-weight:800;letter-spacing:.16em;font-size:20px;">THE HOUSE</div>
          <div style="color:#a1a1aa;font-size:18px;margin-top:3px;">bookmaker consensus · vig removed</div></div>
          <div style="font-size:30px;font-weight:900;color:{GOLD};white-space:nowrap;">{_esc(h['team'])} {_esc(h['score'])} · {h['confidence']}%</div>
        </div>"""
    title = f"{_esc(spec['team_a'])} <span style='color:#52525b'>vs</span> {_esc(spec['team_b'])}"
    body = f"""<div style="color:#a1a1aa;font-size:24px;margin:-6px 0 14px;">{_esc(spec['stage'])}</div>
               {rows}{house}"""
    return _doc(1080, 1350, "5 AIs disagree", title, body, top_align=True)


# --- 2. Contrarian Spotlight ------------------------------------------------

def _contrarian(spec: dict) -> str:
    if not spec.get("dissenter"):
        body = '<div style="font-size:34px;color:#a1a1aa;">No lone dissenter this match — the models mostly agree.</div>'
        return _doc(1080, 1350, "Contrarian Spotlight", "No rogue today", body)
    quote = ""
    if spec.get("reasoning"):
        quote = (f'<div style="margin-top:40px;font-size:30px;font-style:italic;color:#e4e4e7;'
                 f'border-left:5px solid {spec["dissenter_color"]};padding-left:28px;">“{_esc(spec["reasoning"])}”</div>')
    body = f"""
      <div style="display:flex;flex-direction:column;align-items:center;text-align:center;gap:30px;">
        <div style="font-size:120px;">🚨</div>
        {_avatar(spec['dissenter'][0], spec['dissenter_color'], 160)}
        <div style="font-size:56px;font-weight:900;">{_esc(spec['dissenter'])} is going rogue</div>
        <div style="font-size:40px;color:#a1a1aa;">backing <span style="color:#fff;font-weight:800;">{_esc(spec['dissent_team'])}</span>
        while {spec['majority_count']} other AIs ride with <span style="color:#fff;font-weight:800;">{_esc(spec['majority_team'])}</span></div>
      </div>{quote}"""
    return _doc(1080, 1350, "Contrarian Spotlight", "Going Rogue", body)


# --- 3. Bookmaker Challenge -------------------------------------------------

def _bookmaker(spec: dict) -> str:
    def col(label, pct, color):
        return (f'<div style="text-align:center;"><div style="font-size:32px;color:#a1a1aa;font-weight:700;">{label}</div>'
                f'<div style="font-size:170px;font-weight:900;color:{color};line-height:1;">{pct}%</div></div>')
    body = f"""
      <div style="text-align:center;font-size:38px;color:#a1a1aa;margin-bottom:30px;">
        on <span style="color:#fff;font-weight:800;">{_esc(spec['outcome_team'])}</span></div>
      <div style="display:flex;justify-content:space-around;align-items:center;">
        {col('THE HOUSE', spec['book_pct'], GOLD)}
        <div style="font-size:60px;font-weight:900;color:#52525b;">vs</div>
        {col('THE AIs', spec['ai_pct'], BRAND)}
      </div>
      <div style="text-align:center;margin-top:50px;font-size:44px;font-weight:900;">
        {spec['diff_pp']}-point gap. <span style="color:{RED};">Someone's wrong.</span></div>"""
    return _doc(1080, 1350, "Bookies vs Bots", "The Bookmaker Challenge", body)


# --- 4. The Reckoning -------------------------------------------------------

def _reckoning(spec: dict) -> str:
    rows = ""
    for r in spec["rows"]:
        d = r["rank_delta"]
        arrow = (f'<span style="color:{BRAND};">▲ {d}</span>' if d > 0
                 else f'<span style="color:{RED};">▼ {abs(d)}</span>' if d < 0
                 else '<span style="color:#71717a;">–</span>')
        rows += f"""
        <div style="display:flex;align-items:center;gap:24px;padding:20px 0;border-bottom:1px solid #1f1f23;">
          <div style="font-size:34px;font-weight:900;color:#71717a;width:54px;">{r['rank']}</div>
          {_avatar(r['competitor'][0], r['color'])}
          <div style="flex:1;font-size:32px;font-weight:800;">{_esc(r['competitor'])}</div>
          <div style="font-size:30px;font-weight:800;color:#d4d4d8;">{r['total_points']} pts</div>
          <div style="font-size:30px;font-weight:800;width:130px;text-align:right;">{r['points_delta']:+d}</div>
          <div style="font-size:30px;font-weight:800;width:90px;text-align:right;">{arrow}</div>
        </div>"""
    final = f'<div style="color:#a1a1aa;font-size:28px;margin:-10px 0 18px;">Final: {_esc(spec["final"])}</div>' if spec.get("final") else ""
    body = final + rows
    return _doc(1080, 1350, "Standings shifted", "The Reckoning", body, top_align=True)


# --- 5. Vindication / Faceplant ---------------------------------------------

def _vindication(spec: dict) -> str:
    hero, villain = spec.get("hero"), spec.get("villain")
    if not hero:
        body = '<div style="font-size:34px;color:#a1a1aa;">Awaiting the final result…</div>'
        return _doc(1080, 1350, "After the whistle", "Pending", body)

    def panel(emoji, who, color, accent):
        return f"""
        <div style="flex:1;padding:48px;border-radius:24px;background:rgba({accent},.10);border:2px solid rgba({accent},.5);">
          <div style="display:flex;align-items:center;gap:20px;">
            <div style="font-size:72px;">{emoji}</div>
            <div><div style="font-size:28px;font-weight:800;letter-spacing:.12em;color:{color};">{_esc(who['label'])}</div>
            <div style="font-size:46px;font-weight:900;">{_esc(who['competitor'])}</div></div>
          </div>
          <div style="font-size:36px;font-weight:800;margin-top:24px;">{_esc(who['pick'])} · {who['points']} pts</div>
          <div style="font-size:24px;color:#d4d4d8;font-style:italic;margin-top:14px;">“{_esc(who['reasoning'])}”</div>
        </div>"""
    body = f"""
      <div style="color:#a1a1aa;font-size:30px;text-align:center;margin-bottom:30px;">
        {_esc(spec['team_a'])} {_esc(spec['final'])} {_esc(spec['team_b'])}</div>
      <div style="display:flex;flex-direction:column;gap:34px;">
        {panel('🏆', hero, BRAND, '16,185,129')}
        {panel('😬', villain, RED, '239,68,68')}
      </div>"""
    return _doc(1080, 1350, "Hero & villain", "The Verdict", body)


# --- 6. The Receipt ---------------------------------------------------------

def _receipt(spec: dict) -> str:
    rows = ""
    for r in spec["rows"]:
        if r["revealed"]:
            badge = '<span style="color:%s;font-weight:800;">✅ verified</span>' % BRAND if r["verified"] else '<span style="color:%s;font-weight:800;">✗ mismatch</span>' % RED
            pick = f'<span style="font-size:26px;font-weight:800;">{_esc(r["pick"])}</span>'
        else:
            badge = '<span style="color:#71717a;font-weight:800;">🔒 sealed</span>'
            pick = '<span style="color:#52525b;font-size:24px;">sealed until kickoff</span>'
        rows += f"""
        <div style="display:flex;align-items:center;gap:20px;padding:18px 0;border-bottom:1px solid #1f1f23;">
          {_avatar(r['competitor'][0], r['color'], 52)}
          <div style="width:200px;font-size:27px;font-weight:800;">{_esc(r['competitor'])}</div>
          <div style="flex:1;font-family:'Consolas',monospace;font-size:20px;color:#a1a1aa;">{_esc(r['commit_hash'][:24])}…</div>
          <div style="width:230px;text-align:right;">{pick}</div>
          <div style="width:200px;text-align:right;">{badge}</div>
        </div>"""
    head = (f'<div style="color:#a1a1aa;font-size:26px;margin:-10px 0 22px;">'
            f'{_esc(spec["team_a"])} vs {_esc(spec["team_b"])} · {_esc(spec["stage"])} · '
            + ("revealed & verifiable" if spec["revealed"] else "committed, awaiting kickoff") + "</div>")
    body = head + rows
    return _doc(1080, 1350, "Commit → Reveal → Verify", "The Receipt", body, top_align=True)


_RENDERERS = {
    "lineup_card": _lineup,
    "contrarian": _contrarian,
    "bookmaker_challenge": _bookmaker,
    "reckoning": _reckoning,
    "vindication_faceplant": _vindication,
    "receipt": _receipt,
}


def render_card(template: str, image_spec: dict) -> str:
    renderer = _RENDERERS.get(template)
    if renderer is None:
        raise ValueError(f"no card renderer for template {template!r}")
    return renderer(image_spec)
