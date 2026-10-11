# Weekend Gameplan

Friday outing card for the Boyd family (Millersville MD 21108). TokenMax burn build — outdoor plans from weather, sunset, and Chesapeake tides.

Prefers real public **Open-Meteo** (Millersville weather + sunrise/sunset) and **NOAA CO-OPS** predictions for station **8575512 (Annapolis)**. If fetch fails, embeds a clearly labeled EXAMPLE/demo dataset and shows a banner.

## Screens

1. **Home** — weekend strip, kids’ pick toggle, 3 outing cards, rainy-day backup  
2. **Plans** — detailed briefs (spot, tides, alternates)  
3. **Weather** — Fri–Sun forecast table + Annapolis tide extremes  
4. **About** — live vs demo source notes

## Run

```bash
./run.sh          # build + serve http://127.0.0.1:4307/
./run.sh --shots  # + screenshots/
```

Offline single file: `dist/weekend-gameplan.html`

## Layout

- `web/` — index.html, app.css, app.js  
- `data/gameplan.json` — live snapshot (when fetch works)  
- `data/gameplan-demo.json` — EXAMPLE fallback  
- `build.py` / `server.py` / `tests/screenshot.sh`


---
## Repo notes
- **Built:** Oct 2026 (TokenMax build week; see SHORTLIST/ledger), by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/weekend-gameplan` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
- Personal details (emails, phone numbers, home street address) were replaced with `[redacted-…]` placeholders.
