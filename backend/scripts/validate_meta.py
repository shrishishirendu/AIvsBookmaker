"""Discover Meta (Facebook/Instagram) IDs from a single access token.

Set META_TOKEN to a Facebook user access token that has the pages permissions,
then run:  python -m scripts.validate_meta

It prints the exact env values to use:
  META_PAGE_ID, META_PAGE_TOKEN, INSTAGRAM_BUSINESS_ID
so you don't have to hunt for IDs in the Meta dashboards.
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx

GRAPH = "https://graph.facebook.com/v21.0"


async def main() -> None:
    token = os.environ.get("META_TOKEN")
    if not token:
        print("Set META_TOKEN (a Facebook user access token) first."); sys.exit(1)

    async with httpx.AsyncClient(timeout=30) as c:
        # who is this token?
        me = await c.get(f"{GRAPH}/me", params={"access_token": token, "fields": "id,name"})
        if me.status_code != 200:
            print("Token invalid:", me.text[:300]); return
        print("Token belongs to:", me.json().get("name"))

        # pages this user administers (each comes with its own page token)
        pages = await c.get(f"{GRAPH}/me/accounts",
                            params={"access_token": token,
                                    "fields": "id,name,access_token,instagram_business_account"})
        data = pages.json().get("data", [])
        if not data:
            print("No Pages found. Make sure the token has pages_show_list and you admin a Page.")
            return
        for p in data:
            print("\n=== Page:", p.get("name"), "===")
            print("META_PAGE_ID =", p.get("id"))
            print("META_PAGE_TOKEN =", p.get("access_token", "(none — needs pages_manage_posts)"))
            iga = p.get("instagram_business_account")
            if iga:
                print("INSTAGRAM_BUSINESS_ID =", iga.get("id"))
            else:
                print("INSTAGRAM_BUSINESS_ID = (none — link an IG Business account to this Page)")


if __name__ == "__main__":
    asyncio.run(main())
