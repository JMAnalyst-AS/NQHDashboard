#!/usr/bin/env python3
# Builds dashboard/data.json:
# - breaches: unique companies w/ most-recent breach/leak item
# - rss: broader cyber/OSINT (breach-y items filtered out)

import os, sys, subprocess
HERE = os.path.dirname(__file__)
VENDOR = os.path.join(HERE, "_vendor")
os.makedirs(VENDOR, exist_ok=True)
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--target", VENDOR, "feedparser"])
sys.path.insert(0, VENDOR)

import json, datetime, time, re
import feedparser

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")

# ---------- Sources ----------
# Focused, incident-style feeds
BREACH_FEEDS = [
    ("DataBreaches.net", "https://www.databreaches.net/feed/"),
    ("SecurityWeek · Data Breaches", "https://www.securityweek.com/category/data-breaches/feed/"),
    ("BleepingComputer · Data Breach", "https://www.bleepingcomputer.com/feed/tag/data-breach/"),
    ("The Hacker News · Data Breach", "https://thehackernews.com/search/label/Data%20Breach?max-results=20&by-date=true&alt=rss"),
]

# Wider security/OSINT for Q3; we’ll filter out breach-like items
NEWS_FEEDS = [
    ("US-CERT Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("CISA Current Activity", "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml"),
    ("NCSC UK News", "https://www.ncsc.gov.uk/api/1/services/v1/news.rss"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("SecurityWeek", "https://feeds.feedburner.com/Securityweek"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("Microsoft Security Blog", "https://www.microsoft.com/en-us/security/blog/feed/"),
    ("Google Cloud Security", "https://cloud.google.com/blog/topics/identity-security/rss/"),
    ("Cisco Talos", "https://blog.talosintelligence.com/feeds/posts/default"),
    ("ESET WeLiveSecurity", "https://www.welivesecurity.com/feed/"),
    ("Rapid7 Blog", "https://www.rapid7.com/blog/rss/"),
    ("Elastic Security", "https://www.elastic.co/security-labs/rss.xml"),
    ("Wiz Research", "https://www.wiz.io/blog/rss.xml"),
    ("Bellingcat", "https://www.bellingcat.com/feed/"),
    ("OSINTCurious", "https://osintcurio.us/feed/"),
]

# Keywords that indicate a breach/leak headline (used to filter OUT of Q3)
BREACH_KEYWORDS = re.compile(
    r"(data breach|breach|leak|database leak|stolen data|exposed data|ransomware|extortion|hack(ed)?)",
    re.IGNORECASE,
)

# Threat-actor / group names to avoid treating as "org"
ACTOR_STOPWORDS = {
    "lockbit","alphv","blackcat","qilin","dragondforce","dragonforce","clop","conti",
    "revil","maze","babuk","blackbasta","lapssus","lapsus","ragnar","snatch","play",
    "cuba","ransomexx","royal","blackbyte","akira","medusa","hive","trigona","noescape",
    "ransomhouse","8base","hunters","blacksuit","mangozero","zedo","bandidos"
}

# Company suffixes removed for normalization
SUFFIXES = [
    "inc","inc.","ltd","ltd.","llc","plc","gmbh","ag","s.a.","s.a","s.p.a","spa",
    "co","co.","corp","corp.","corporation","company","group","holdings","limited"
]

def _ts(entry):
    s = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", s) if s else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _org_from_title(title: str) -> str:
    """Grab likely company name from the start of the headline."""
    t = re.sub(r"[“”\"']", "", (title or "")).strip()
    # Try common separators first
    for pat in (r"^(.*?)\s*:\s*", r"^(.*?)\s*[–—-]\s*", r"^(.*?)\s*\|\s*"):
        m = re.search(pat, t)
        if m and m.group(1): return m.group(1).strip()
    # Fallback: take words before breach-y keyword
    m = re.search(r"^(.*?)\s*(?:data breach|breach|leak|hacked|cyber attack)", t, flags=re.IGNORECASE)
    if m and m.group(1): return m.group(1).strip()
    # Final fallback: first 5 words
    return " ".join(t.split()[:5])

def _normalize_org(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)               # remove punctuation
    parts = [p for p in s.split() if p not in SUFFIXES]
    s = " ".join(parts)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _looks_like_actor(org_norm: str) -> bool:
    return any(token in ACTOR_STOPWORDS for token in org_norm.split())

def _dedupe(items, key="title"):
    seen, out = set(), []
    for it in items:
        k = it.get(key, "")
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out

def build_breaches(per_feed=12, cap=25):
    """Return ONE item per company (most recent), excluding actor names."""
    candidates = []
    for name, url in BREACH_FEEDS:
        feed = feedparser.parse(url)
        taken = 0
        for e in feed.entries:
            if taken >= per_feed: break
            title = (e.get("title") or "").strip()
            if not title: continue
            ts = _ts(e)
            org = _org_from_title(title)
            org_norm = _normalize_org(org)
            # skip if it looks like a threat-actor headline
            if not org_norm or _looks_like_actor(org_norm):
                continue
            candidates.append({
                "org": org.strip(),
                "org_norm": org_norm,
                "title": title,
                "source": name,
                "link": e.get("link", ""),
                "published": e.get("published", "") or ts,
                "ts": ts,
            })
            taken += 1

    # Keep only the newest item per org_norm
    latest_by_org = {}
    for it in candidates:
        k = it["org_norm"]
        if k not in latest_by_org or it["ts"] > latest_by_org[k]["ts"]:
            latest_by_org[k] = it

    items = list(latest_by_org.values())
    items.sort(key=lambda x: x["ts"], reverse=True)
    if not items:
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        items = [
            {"org": "ExampleCo", "title": "ExampleCo confirms data breach", "source": "Demo", "link": "", "published": now, "ts": now},
        ]
    # Strip helper field before writing
    for it in items:
        it.pop("org_norm", None)
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
            # filter OUT breach-like items so Q3 doesn’t duplicate Q1
            if BREACH_KEYWORDS.search(title): 
                continue
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
        "summary": "Unique companies with most-recent breach/leak, plus curated security & OSINT RSS.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("[ok] wrote", OUT)

if __name__ == "__main__":
    build()
