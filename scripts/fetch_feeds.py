#!/usr/bin/env python3
# Build dashboard/data.json from open sources:
# - Pulsedive indicators (Breach/Leak quadrant)
# - URLhaus recent URLs (fallback/augment)
# - Curated RSS feeds (Security News quadrant)

# --- ensure feedparser is available immediately ---
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "feedparser"])

import os, json, datetime, time, ssl, urllib.request, re
import feedparser  # now guaranteed installed

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")

UA = "NorthQuay-OSINT-TV/1.0 (+github pages dashboard)"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()

# ---------- Indicator helpers ----------
def classify(indicator: str) -> str:
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", indicator):
        return "ip"
    if indicator.startswith(("http://", "https://")):
        return "url"
    return "domain"

def pulsedive(limit=25):
    """Fetch open feed from pulsedive.com"""
    url = "https://pulsedive.com/feed/?format=json"
    out = []
    try:
        raw = fetch_url(url)
        data = json.loads(raw.decode("utf-8"))
        for it in data[:limit]:
            ind = it.get("indicator")
            if not ind:
                continue
            out.append({
                "name": ind,
                "type": it.get("type") or classify(ind),
                "risk": it.get("risk") or ""
            })
    except Exception as e:
        print(f"[warn] pulsedive: {e}")
    return out

def urlhaus(limit=25):
    """Fallback from abuse.ch URLhaus API"""
    out = []
    try:
        raw = fetch_url("https://urlhaus-api.abuse.ch/v1/urls/recent/")
        data = json.loads(raw.decode("utf-8"))
        for u in data.get("urls", [])[:limit]:
            ind = u.get("url") or u.get("host")
            if not ind:
                continue
            out.append({
                "name": ind,
                "type": "url" if ind.startswith("http") else classify(ind),
                "risk": (u.get("url_status") or "").lower()
            })
    except Exception as e:
        print(f"[warn] urlhaus: {e}")
    return out

def build_threats():
    """Combine Pulsedive + URLhaus, dedupe, seed fallback"""
    items = pulsedive(limit=25) + urlhaus(limit=25)
    seen, deduped = set(), []
    for it in items:
        k = it.get("name")
        if not k or k in seen:
            continue
        seen.add(k)
        deduped.append({
            "name": k,
            "type": it.get("type") or classify(k),
            "risk": it.get("risk") or ""
        })
    if not deduped:
        deduped = [
            {"name": "demo.indicator", "type": "domain", "risk": "low"},
            {"name": "1.2.3.4", "type": "ip", "risk": "medium"},
        ]
    return deduped[:25]

# ---------- RSS Feeds ----------
RSS_FEEDS = [
    # Government / CERT
    ("US-CERT Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("CISA Current Activity", "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml"),
    ("NCSC UK News", "https://www.ncsc.gov.uk/api/1/services/v1/news.rss"),

    # Major security outlets
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

    # OSINT sources
    ("Bellingcat", "https://www.bellingcat.com/feed/"),
    ("OSINTCurious", "https://osintcurio.us/feed/"),
]

def rss_items(per_feed=6, total_cap=40):
    items, seen_titles = [], set()
    for name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            taken = 0
            for entry in feed.entries:
                if taken >= per_feed:
                    break
                title = (entry.get("title") or "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                published = entry.get("published") or entry.get("updated") or ""
                ts_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                if ts_struct:
                    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts_struct)
                else:
                    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                items.append({
                    "title": title,
                    "published": published or ts,
                    "source": name,
                    "link": entry.get("link", ""),
                    "ts": ts,
                })
                taken += 1
        except Exception as e:
            print(f"[warn] rss {name}: {e}")

    # Sort newest first
    def _key(x):
        try:
            return datetime.datetime.strptime(x["ts"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return datetime.datetime.utcnow()
    items.sort(key=_key, reverse=True)
    return items[:total_cap]

# ---------- Build and write JSON ----------
def build():
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "threats": build_threats(),
        "rss": rss_items(),
        "summary": (
            "Open-source wallboard: Pulsedive + URLhaus indicators; "
            "curated security & OSINT RSS. Add internal/commercial sources server-side as needed."
        ),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("[ok] wrote", OUT)

if __name__ == "__main__":
    build()
