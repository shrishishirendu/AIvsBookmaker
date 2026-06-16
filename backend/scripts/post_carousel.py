"""One-off: post a multi-image (carousel) LinkedIn update with a caption.

Registers each image as a LinkedIn asset, uploads the bytes, then publishes a
single ugcPost referencing all of them (a swipeable multi-image post).
Run:  python -m scripts.post_carousel
"""
from __future__ import annotations

import asyncio
import sys

import httpx

from app.config import settings

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MATCH_DIR = "generated/cards/1489371"
IMAGES = [
    (f"{MATCH_DIR}/lineup_card.png", "The Lineup — 5 AIs disagree"),
    (f"{MATCH_DIR}/receipt.png", "The Receipt — verified"),
    (f"{MATCH_DIR}/vindication_faceplant.png", "The Verdict"),
]

CAPTION = """🤖⚽ Every AI company says their model is smart. Almost none will tell you what it predicted BEFORE the outcome — and prove they didn't change it after.

That gap is what I'm building into a product.

I'm putting the five leading AI models — Claude, ChatGPT, Gemini, Grok, and DeepSeek — head-to-head on the hardest public test of judgment there is: predicting every match of the FIFA World Cup 2026. Same prompt, same moment, no edits. They disagree constantly — and that disagreement is the product.

The wedge: accountability. Before every kickoff, each model's prediction is cryptographically hashed (SHA-256) and published. The pick is sealed until the match starts, then revealed — and anyone can re-hash it to prove it's untouched. AI predictions with receipts. Then they're scored against the real result AND the bookmakers. Can the machines beat the house?

Why this is a company, not a gimmick:
→ A live, verifiable benchmark of frontier models on real-world forecasting under uncertainty — something static evals can't give you.
→ It runs fully autonomously — predicts, scores, generates the graphics, and publishes itself, every match.
→ A daily content engine with built-in drama: emergent model "personalities," upsets, vindications, and a public leaderboard where soon YOU compete against the AIs.

The bigger bet: as AI makes higher-stakes calls, "trust me" stops being good enough. "Here's the cryptographic proof of exactly what I said, and when" becomes the standard. Football is the wedge. Verifiable, accountable AI is the market.

It's live and posting on its own right now. This is day one.

If you're building in AI, sports, or trust infrastructure — or you just want to watch five AIs argue and get humbled by reality — follow along. 👇

Which model finishes top of the table? Call it now.

#AI #LLM #Startup #BuildInPublic #WorldCup2026 #VerifiableAI"""


async def register_image(client, headers, author, path) -> str:
    reg = await client.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={"registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author,
            "serviceRelationships": [{"relationshipType": "OWNER",
                                      "identifier": "urn:li:userGeneratedContent"}]}},
    )
    reg.raise_for_status()
    val = reg.json()["value"]
    upload_url = val["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset = val["asset"]
    with open(path, "rb") as fh:
        up = await client.put(upload_url,
                              headers={"Authorization": headers["Authorization"]},
                              content=fh.read())
        up.raise_for_status()
    return asset


async def main() -> None:
    token = settings.linkedin_access_token
    author = settings.linkedin_author_urn
    if not token or not author:
        print("Missing LinkedIn credentials"); return
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}

    async with httpx.AsyncClient(timeout=60) as client:
        media = []
        for path, title in IMAGES:
            asset = await register_image(client, headers, author, path)
            media.append({"status": "READY", "media": asset, "title": {"text": title}})
            print("uploaded:", path, "->", asset)

        body = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": CAPTION},
                "shareMediaCategory": "IMAGE",
                "media": media,
            }},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        r = await client.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body)
        if r.status_code >= 300:
            print("POST FAILED", r.status_code, r.text[:400]); return
        ext = r.headers.get("x-restli-id") or r.json().get("id", "")
        print("POSTED carousel ->", ext)


if __name__ == "__main__":
    asyncio.run(main())
