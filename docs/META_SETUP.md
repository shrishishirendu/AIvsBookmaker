# Wiring Facebook + Instagram (Meta) — what you do, what I do

The publishers are already built; Meta just needs credentials only you can create.
Everything below is the part that requires your Meta/Facebook login.

## What you need to create (≈15–20 min)

1. **A Facebook Page** (if you don't have one) — facebook.com → Pages → Create.
   This is what posts will appear on (Meta has no "personal profile" API).

2. **An Instagram Business or Creator account**, **linked to that Page**.
   - In the Instagram app: Settings → *Account type* → switch to **Business/Creator**.
   - Link it to the Facebook Page (Instagram Settings → *Linked accounts*, or via the
     Page's *Linked accounts* in Meta Business settings).

3. **A Meta app** — developers.facebook.com → *My Apps* → **Create App** → type
   **"Business"**. Add the **"Facebook Login"** and **"Instagram Graph API"** products.

4. **An access token** with these permissions (scopes):
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`   ← lets us post to the Page
   - `instagram_basic`
   - `instagram_content_publish`  ← lets us post to Instagram
   Easiest source: developers.facebook.com → **Graph API Explorer** → pick your app →
   *Generate Access Token* → tick those scopes → generate. Copy the token.

   > Note: while your app is in **Development mode**, these permissions work for
   > **you and any Page/IG you admin** without full App Review. Full public review is
   > only needed if other people's accounts will post — not your case. So you can go
   > live on your own Page/IG without waiting on Meta review.

## Then send me the token and I'll do the rest

Paste me that token. I'll run `scripts/validate_meta.py` to auto-derive:

```
META_PAGE_ID=...
META_PAGE_TOKEN=...        (the long-lived Page token)
INSTAGRAM_BUSINESS_ID=...
```

…and set them (plus `MEDIA_BASE_URL=<the Railway URL>` so Instagram can fetch the
card images) on Railway. After that, the scheduler auto-posts to **LinkedIn +
Facebook + Instagram** together — same cards, same hooks, same site link.

## Gotchas I've already handled in code
- **Instagram needs a public image URL** — handled via `MEDIA_BASE_URL` (the backend
  serves the cards at `/static`, reachable on the Railway domain).
- **Facebook** uploads the image bytes directly (no public URL needed).
- Missing creds never crash a post — that platform is simply skipped.
