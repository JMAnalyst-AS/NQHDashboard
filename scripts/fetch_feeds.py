#!/usr/bin/env python3
# Build dashboard/data.json:
# - breaches: recent company breach/leak headlines (news-first)
# - rss: broader cyber + OSINT headlines
# Vendored feedparser so GH Actions always succeeds.

import os, sys, subprocess
HERE = os.path.dirname(__file__)
VENDOR = os.path.join(HERE, "_vendor")
os.makedirs(VENDOR, exist_ok=True)
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--target", VENDOR, "feedparser"])
sys.path.insert(0, VENDOR)

import json, datetime, time, re
import feedparser

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")

# --- Dedicated breach/leak sources (tagged feeds) ---
BREACH_FEEDS = [
    ("DataBreaches.net", "https://www.databreaches.net/feed/"),
    ("BleepingComputer (Data Breach)", "https://www.bleepingcomputer.com/feed/tag/data-breach/"),
    ("The Hacker News (Data Breach)", "https://thehackernews.com/search/label/Data%20Breach?max-results=20&by-date=true&alt=rss"),
    # SecurityWeek has topic feeds behind feedburner; we’ll keyword-filter its main feed below
]

# --- Broader security feeds we will keyword-filter for breaches ---
SEC_FEEDS_FOR_BREACH = [
    ("SecurityWeek", "https://feeds.feedburner.com/Securityweek"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
]

# --- Existing news panel sources (unchanged) ---
NEWS_FEEDS = [
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

BREACH_KEYWORDS = re.compile(
    r"(data breach|breach|leak|ransomware|stolen data|exposed data|compromise|attack)",
    re.IGNORECASE,
)

def _ts(entry):
    s = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if s:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", s)
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

ORG_PATTERNS = [
    r"^(.*?)\s*:\s*", r"^(.*?)\s*[–—-]\s*", r"^(.*?)\s*\|\s*",
    r"^(.*?)\s*data breach", r"^(.*?)\s*cyber attack", r"^(.*?)\s*breach", r"^(.*?)\s*hacked",
]
def _org_from_title(title: str) -> str:
    t = re.sub(r"[“”\"']", "", title or "").strip()
    for pat in ORG_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m and m.group(1):
            org = m.group(1).strip(" -—:|")
            if 2 <= len(org) <= 80:
                return org
    return " ".join(t.split()[:5])  # fallback

def _dedupe(items, key="title"):
    seen, out = set(), []
    for it in items:
        k = it.get(key, "")
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out

def build_breaches(per_feed=10, cap=40):
    items = []
    # 1) Dedicated breach feeds
    for name, url in BREACH_FEEDS:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed: break
            title = (e.get("title") or "").strip()
            if not title: continue
            ts = _ts(e)
            items.append({
                "org": _org_from_title(title),
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts,
            })
            taken += 1

    # 2) Keyword-filter broader feeds
    for name, url in SEC_FEEDS_FOR_BREACH:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed: break
            title = (e.get("title") or "").strip()
            if not title or not BREACH_KEYWORDS.search(title): continue
            ts = _ts(e)
            items.append({
                "org": _org_from_title(title),
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts,
            })
            taken += 1

    # Clean up: dedupe & sort newest first
    items = _dedupe(items, key="title")
    items.sort(key=lambda x: x["ts"], reverse=True)

    # Safety: seed a couple if empty
    if not items:
        items = [
            {"org": "ExampleCo", "title": "ExampleCo reports data breach affecting users", "source": "Demo", "link": "", "published": "", "ts": _ts(type("x",(object,),{})())},
            {"org": "Acme Ltd", "title": "Acme Ltd confirms ransomware incident", "source": "Demo", "link": "", "published": "", "ts": _ts(type("x",(object,),{})())},
        ]
    return items[:cap]

def build_news(per_feed=6, cap=40):
    items = []
    for name, url in NEWS_FEEDS:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed: break
            title = (e.get("title") or "").strip()
            if not title: continue
            ts = _ts(e)
            items.append({
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts,
            })
            taken += 1
    items = _dedupe(items, key="title")
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:cap]

def build():
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "breaches": build_breaches(),
        "rss": build_news(),
        "summary": "Open-source wallboard: company breach/leak headlines + curated security & OSINT RSS.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("[ok] wrote", OUT)

if __name__ == "__main__":
    build()
