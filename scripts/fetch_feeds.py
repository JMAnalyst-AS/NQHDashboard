#!/usr/bin/env python3
# Build dashboard/data.json:
# - breaches: recent company breach/leak headlines (RSS)
# - rss: broader cyber + OSINT headlines (RSS)
# NOTE: we vendor feedparser so imports always work on GitHub Actions.

import os, sys, subprocess
HERE = os.path.dirname(__file__)
VENDOR = os.path.join(HERE, "_vendor")
os.makedirs(VENDOR, exist_ok=True)
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--target", VENDOR, "feedparser"])
sys.path.insert(0, VENDOR)

import json, datetime, time, re
import feedparser

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")

# ---------------- Breach / Leak sources (news) ----------------
BREACH_FEEDS = [
    ("DataBreaches.net", "https://www.databreaches.net/feed/"),
    ("BleepingComputer (Data Breach)", "https://www.bleepingcomputer.com/feed/tag/data-breach/"),
    ("The Hacker News (Data Breach)", "https://thehackernews.com/search/label/Data%20Breach?max-results=20&by-date=true&alt=rss"),
]

# ---------------- Security & OSINT (existing RSS) -------------
RSS_FEEDS = [
    # Government / CERT
    ("US-CERT Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("CISA Current Activity", "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml"),
    ("NCSC UK News", "https://www.ncsc.gov.uk/api/1/services/v1/news.rss"),

    # Major outlets
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("SecurityWeek", "https://feeds.feedburner.com/Securityweek"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),

    # Vendor intel / research
    ("Microsoft Security Blog", "https://www.microsoft.com/en-us/security/blog/feed/"),
    ("Google Cloud Security", "https://cloud.google.com/blog/topics/identity-security/rss/"),
    ("Cisco Talos", "https://blog.talosintelligence.com/feeds/posts/default"),
    ("ESET WeLiveSecurity", "https://www.welivesecurity.com/feed/"),
    ("Rapid7 Blog", "https://www.rapid7.com/blog/rss/"),
    ("Elastic Security", "https://www.elastic.co/security-labs/rss.xml"),
    ("Wiz Research", "https://www.wiz.io/blog/rss.xml"),

    # OSINT
    ("Bellingcat", "https://www.bellingcat.com/feed/"),
    ("OSINTCurious", "https://osintcurio.us/feed/"),
]

# -------- helpers --------
def _norm_ts(entry):
    ts_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if ts_struct:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", ts_struct)
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

ORG_PATTERNS = [
    r"^(.*?)\s*:\s*",                      # "Acme Corp: suffers breach"
    r"^(.*?)\s*–\s*",                      # "Acme – Data breach ..."
    r"^(.*?)\s*—\s*",
    r"^(.*?)\s*\|\s*",
    r"^(.*?)\s*data breach",               # "... data breach ..."
    r"^(.*?)\s*cyber attack",
    r"^(.*?)\s*breach",
    r"^(.*?)\s*hacked",
]

def _extract_org(title: str) -> str:
    t = re.sub(r"[“”\"']", "", title or "").strip()
    for pat in ORG_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m and m.group(1):
            org = m.group(1).strip(" -—:|")
            if 2 <= len(org) <= 80:
                return org
    # fallback: first 5 words
    return " ".join(t.split()[:5])

def build_breaches(per_feed=10, cap=40):
    items, seen = [], set()
    for name, url in BREACH_FEEDS:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed:
                break
            title = (e.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            ts = _norm_ts(e)
            items.append({
                "org": _extract_org(title),
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts
            })
            taken += 1
    # newest first
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:cap]

def build_news(per_feed=6, cap=40):
    items, seen = [], set()
    for name, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed:
                break
            title = (e.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            ts = _norm_ts(e)
            items.append({
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts
            })
            taken += 1
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:cap]

def build():
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "breaches": build_breaches(),
        "rss": build_news(),
        # Keep summary text generic
        "summary": "Open-source wallboard: breach/leak headlines + curated security & OSINT RSS.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("[ok] wrote", OUT)

if __name__ == "__main__":
    build()
