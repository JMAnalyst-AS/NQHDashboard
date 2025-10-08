#!/usr/bin/env python3
# Build data.json from open feeds: Pulsedive (indicators) + curated RSS.
import os, sys, json, datetime, urllib.request, ssl, xml.etree.ElementTree as ET

OUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data.json")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RSS_FEEDS = [
  ("US-CERT Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml"),
  ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
  ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
]

def get_url(url, timeout=30):
  try:
    with urllib.request.urlopen(url, timeout=timeout, context=CTX) as r:
      return r.read()
  except Exception as e:
    sys.stderr.write(f"[warn] fetch {url} failed: {e}\n")
    return None

def pulsedive():
  url = "https://pulsedive.com/feed/?format=json"
  raw = get_url(url)
  out = []
  if raw:
    try:
      data = json.loads(raw.decode("utf-8"))
      for it in data[:20]:
        out.append({"name": it.get("indicator"), "type": it.get("type"), "risk": it.get("risk")})
    except Exception as e:
      sys.stderr.write(f"[warn] pulsedive parse: {e}\n")
  return out

def rss_items():
  items = []
  for name, url in RSS_FEEDS:
    raw = get_url(url)
    if not raw: 
      continue
    try:
      root = ET.fromstring(raw)
      for it in root.findall(".//item")[:10]:
        title = it.findtext("title") or ""
        pub = it.findtext("pubDate") or ""
        items.append({"title": title, "published": pub, "source": name})
    except Exception as e:
      sys.stderr.write(f"[warn] rss parse {name}: {e}\n")
  return items[:20]

def build():
  payload = {
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "threats": pulsedive(),
    "rss": rss_items(),
    "summary": "Open-source wallboard: Pulsedive indicators + curated security RSS. Add internal/commercial sources server-side as needed."
  }
  os.makedirs(os.path.dirname(OUT), exist_ok=True)
  with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
  print("[ok] wrote", OUT)

if __name__ == "__main__":
  build()
