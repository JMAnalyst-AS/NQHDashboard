# North Quay — OSINT TV (Four Quadrants, Clean)

Single-screen **2×2 dashboard**:
1) Breach/Leak Intelligence (Pulsedive) — top-left
2) **Live Global Threat Map** (Kaspersky widget) — top-right
3) Security News (RSS: US‑CERT, BleepingComputer, Krebs) — bottom-left
4) Daily Intelligence Summary — bottom-right

## Deploy (one workflow does everything)
This repo includes a single workflow: `.github/workflows/site.yml`  
It **rebuilds `dashboard/data.json` AND deploys GitHub Pages**:
- Hourly (cron)
- On push to `main` affecting site files
- On manual dispatch (Run workflow)

### Steps
1. Create a public repo and upload this folder’s contents.
2. Go to **Settings → Pages → Source = GitHub Actions**.
3. Go to **Actions → Build data & Deploy Pages** → **Run workflow** once.
4. Your live URL appears on **Settings → Pages**.

## Customize
- Add RSS feeds in `scripts/fetch_feeds.py` (`RSS_FEEDS` list).
- Replace `dashboard/assets/logo.jpg` with your logo.
- Tweak colors/layout in `dashboard/style.css`.
- If Kaspersky is blocked on your device, replace the iframe with another embeddable source,
  or use a self-hosted globe: `<iframe src="./map/index.html">`.
