#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds dashboard/data.json with:
- segment1 / hacks: single-source "recent hacks on companies"
- segment3 / rss: multi-source Cyber + OSINT feed

No Pulsedive. Uses only public RSS/Atom endpoints.
"""

import json
import os
import datetime
import requests
import feedparser

UA = "NQHDashboard/1.0 (+https://github.com/JMAnalyst-AS/NQHDashboard)"
TIMEOUT = 20

S = requests.Session()
S.headers.update({
    "User-Agent": UA,
    "Accept": "application/rss+xml, application/atom+xml, */*"
})

# -------- Segment 1: a SINGLE reliable feed for company hacks ----------
# DataBreaches.net — focused on breaches/hacks against organisations
HACKS_FEED = "https://databreaches.net/feed/"

# -------- Segment 3: mixed Cyber + OSINT sources -----------------------
# Keep this broad and high-signal. Add/remove as you like.
CYBER_OSINT_FEEDS = [
    # Official/Gov security advisories & news
    "https://www.cisa.gov/news-events/cybersecurity-advisories.xml",   # CISA advisories
    "https://www.cisa.gov/news-events/alerts.xml",                      # CISA alerts
    "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed",           # NCSC (UK) aggregate
    # News & analysis
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://thehackernews.com/feeds/posts/default",                    # Atom
    # OSINT-focused publications
    "https://www.bellingcat.com/feed/",
    "https://osintcurio.us/feed/",
    "https://sector035.nl/feed"                                         # Weekly OSINT roundup
]

def fetch_feed(url: str, limit: int = 25):
    """Fetch a feed with a real UA from CI, parse once, and normalize items."""
    try:
        r = S.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
    except Exception:
        return []

    src_title = parsed.feed.get("title") or url
    out = []
    for e in parsed.entries[:limit]:
        out.append({
            "title": getattr(e, "title", "") or "",
            "url": getattr(e, "link", "") or "",
            "published": getattr(e, "published", "") \
                or getattr(e, "updated", "") \
                or getattr(e, "dc_date", "") \
                or "",
            "source": src_title
        })
    return out


def dedupe_by_url(items):
    seen, result = set(), []
    for it in items:
        u = (it.get("url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            result.append(it)
    return result


def build_payload():
    # Segment 1 (single feed: recent hacks on companies)
    hacks = fetch_feed(HACKS_FEED, limit=30)

    # Segment 3 (Cyber + OSINT multi-source)
    all_items = []
    for url in CYBER_OSINT_FEEDS:
        all_items.extend(fetch_feed(url, limit=20))
    rss = dedupe_by_url(all_items)

    now = datetime.datetime.utcnow().isoformat() + "Z"
    payload = {
        "generated_at": now,

        # Segment 1 (top-left)
        "segment1": hacks,
        "hacks": hacks,   # alias for existing front-ends

        # Segment 3 (cyber + OSINT)
        "segment3": rss,
        "rss": rss        # alias for existing front-ends now
    }
    return payload


def main():
    data = build_payload()
    os.makedirs("dashboard", exist_ok=True)
    out_path = os.path.join("dashboard", "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} with {len(data['segment1'])} hacks "
          f"and {len(data['segment3'])} cyber/OSINT items at {data['generated_at']}.")


if __name__ == "__main__":
    main()
