# Backlog
*Every request gets a number. Status: Idea → Agreed → Built (date) → Released (date).*

| # | Request | Status |
|---|---|---|
| W-001 | Downloader: IFS, AIFS, IFS ensemble (east coast only) | Built 18 Oct |
| W-002 | Seasonal: ECMWF SEAS5 from Copernicus | Built 18 Oct |
| W-003 | Screen at 8892: Short / Medium / AI vs IFS / Seasonal / Map (S1, M1, C1, L1, G1, G2, A1) | Built 18 Oct |
| W-004 | Panel cards for every panel + MODELS.md | Done 18 Oct |
| W-005 | Short (S1): ensemble 10–90 % range band + AIFS line + rain chance | Built 18 Oct |
| W-006 | BOM city forecasts (max / min / rain / chance) beside ECMWF on S1 and M1 | Built 18 Oct |
| W-007 | BOM ACCESS-S2 seasonal beside ECMWF SEAS5 on L1 (Copernicus, same key) | Built 18 Oct |
| W-008a | Record BOM observations (daily high/low/rain/sun/gust + half-hourly) on every refresh | Built 18 Oct |
| W-008b | BOM correction: learn each city's usual error (by lead time, time of day), show "ECMWF corrected" | Agreed – needs 2–4 weeks of pairs (from ~mid Nov) |
| W-009 | **AIFS ENS** – ECMWF AI ensemble (range from the AI model), ~+12 GB per refresh | Idea – later |
| W-010 | **NOAA GFS / GEFS** – US model + ensemble as independent second opinion, +2–10 GB | Idea – later |
| W-024 | **Overnight data on the trading PC by 8 am Sydney**: cloud jobs 6:52 + 7:22 am, 11:47 am (midday IFS), 7:17 pm (full) Sydney; seasonal checked every job (only when due) and published after the forecasts; Weather.exe checks every 15 min; this PC starts the jobs (Task Scheduler) while GitHub's timer is late | Built 21–23 Oct, released 23 Oct |
| W-025 | Pages Short / Medium / Seasonal / Map only (AI vs IFS page removed); **one field picker in the top bar** for all region charts on a page; **I1 price tags** (▲ / ▼ + reason) | Built 23 Oct – not released |
| W-026 | **Week-ahead grid**: states × days, coloured hot / cold / lull / dull / wet, ▲ / ▼ price arrows | Built 23 Oct – user OK |
| W-027 | **Wind and solar at the farm areas** (not the capital city square) | Built 23 Oct – user OK, first data 23 Oct evening |
| W-028 | **Alerts** when a new run changes something big (red dot on the tab, optional sound / pop-up) | Built 23 Oct – user OK |
| W-029 | **Linked charts**: hover one state = same time on all; click a day = highlight everywhere | Built 23 Oct – user OK |
| W-030 | **Click a city on the map** opens its chart; **keyboard shortcuts** (1–4 pages, T / R / S / W field) | Built 23 Oct – testing |
| W-014 | **Forecast check**: yesterday's forecasts vs what BOM measured, per model (better from ~mid Nov) | Agreed 23 Oct – step 6 |
| W-011a | **CFS (US, NOAA CFSv2)** seasonal as a third model on L1 + map (Copernicus monthly, same key) | Built 21 Oct – not released |
| W-011 | Other seasonal centres on Copernicus (UK Met Office, Météo-France, DWD, Japan, Canada) | Idea – later |
| W-012 | Automatic refresh: Weather.exe checks the cloud (hourly; every 15 min since W-024), fetches only new NEM-only runs (~60 MB each) | Built 20 Oct (with W-019) |
| W-013 | Package Weather.exe (one window, one screen) | **Released 20 Oct** – `2. Output\Weather.zip` + `Weather (update).zip` |
| W-018 | Refresh button in the screen: Full (~18 GB) / Without ensemble (~1.5 GB) / BOM only; keeps the PC awake while downloading | Built 20 Oct (in the exe) |
| W-015 | Editable screen like NEM Trader: Edit mode, add / move / resize / remove panels, pages add / rename / copy / delete / reset; region + field picker per panel; ⓘ help from cards. One window, one screen (no multi-monitor) | Built 20 Oct |
| W-016 | Download progress (%) on screen while a refresh runs (header + A1) | Built 20 Oct |
| W-017 | Compare runs: run + vs pickers on S1 / M1 / L1 / G1 (dashed older run, Change column, change map) + new D1 "What changed" panel | Built 20 Oct |
| W-019 | Cloud refresh on GitHub (public project `nem-weather`): a GitHub job downloads ECMWF at 7 am (no ensemble) and 7 pm (full), keeps only the NEM east coast, publishes it (last 30 days); Weather.exe picks it up. Copernicus key = GitHub secret. Direct ECMWF download kept as back-up | Built 20 Oct – first jobs OK (light 4 min, seasonal 2 min) |
| W-020 | Keep the GitHub schedule alive: GitHub turns off scheduled jobs after 60 days without code uploads – add a small monthly "still alive" upload (due before ~19 Dec 2026) | Idea 20 Oct |
| W-021 | I1 Insights panel (rules, plain words) for Short / Medium / AI vs IFS / Seasonal: what stands out + what changed vs yesterday, NSW/QLD/VIC/SA; on each page where TAS was. Built-in pages follow the user's layout without TAS | Built 20 Oct |
| W-022 | Ensemble max / min over all 24 hours: extra max/min-only steps (feed `ensx`, ~2.8 GB / run in the cloud) – fixes too-warm lows and missed late / early peaks in M1 table + I1 | Built 20 Oct – cloud 2.6 GB in 2 min, 48 KB file; lows up to 2.6 °C cooler (SA) |
| W-023 | Map (G1): Play / Pause button that steps through the times by itself (loops), speed Slow / Normal / Fast | Built 20 Oct |
| W-014 | "Forecast check" panel: ECMWF / BOM forecast vs what actually happened, per city | Idea – after W-008b |
