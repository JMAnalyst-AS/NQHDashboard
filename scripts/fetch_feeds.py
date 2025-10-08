#!/usr/bin/env python3
# Build dashboard/data.json from open sources:
# - Pulsedive indicators  (Breach/Leak quadrant)
# - Curated RSS feeds     (Security News quadrant)

import os, sys, json, datetime, time, ssl, subprocess, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")

# --- Ensure feedparser is available (installs on GH Actions runner if needed) ---
try:
    import feedparser  # type: ignore
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser", "-q"])
    import feedparser  # type: ignore

# --- Networking helpers ---
UA = "NorthQuay-OSINT-TV/1.0 (+github pages dashboard)"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()

# --- Pulsedive (open feed) ---
def pulsedive(limit=25):
    url = "https://pulsedive.com/feed/?format=json"
    out = []
    try:
        raw = fetch_url(url)
        data = json.loads(raw.decode("utf-8"))
        for it in data[:limit]:
            out.append(
                {
                    "name": it.get("indicator"),
                    "type": it.get("type"),
                    "risk": it.get("risk"),
                }
            )
    except Exception as e:
        sys.stderr.write(f"[warn] pulsedive: {e}\n")
    return out

# --- RSS feeds (cyber + OSINT) ---
# You can freely add/remove feeds here.
RSS_FEEDS = [
    # Government / CERT
    ("US-CERT Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("CISA Current Activity", "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml"),
    ("NCSC UK News", "https://www.ncsc.gov.uk/api/1/services/v1/news.rss"),

    # Major security news
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

    # OSINT-focused
    ("Bellingcat", "https://www.bellingcat.com/feed/"),
    ("OSINTCurious", "https://osintcurio.us/feed/"),
]

def rss_items(per_feed=8, total_cap=40):
    items = []
    seen_titles = set()

    for name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= per_feed:
                    break
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                # Prefer published, then updated; fall back to now
                published = entry.get("published") or entry.get("updated") or ""
                # Normalize structured time if present
                ts = None
                for k in ("published_parsed", "updated_parsed"):
                    if getattr(entry, k, None):
                        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", getattr(entry, k))
                        break
                if not ts:
                    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                items.append(
                    {
                        "title": title,
                        "published": published or ts,
                        "source": name,
                        "link": entry.get("link", ""),
                        "ts": ts,  # sortable timestamp
                    }
                )
                count += 1
        except Exception as e:
            sys.stderr.write(f"[warn] rss {name}: {e}\n")

    # Sort newest first by our normalized ts
    def _key(x):
        try:
            return datetime.datetime.strptime(x["ts"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return datetime.datetime.utcnow()

    items.sort(key=_key, reverse=True)
    return items[:total_cap]

# --- Build payload ---
def build():
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "threats": pulsedive(),
        "rss": rss_items(),
        "summary": (
            "Open-source wallboard: Pulsedive indicators + curated security & OSINT RSS. "
            "Add internal/commercial sources server-side as needed."
        ),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("[ok] wrote", OUT)

if __name__ == "__main__":
    build()
