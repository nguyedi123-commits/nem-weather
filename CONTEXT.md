# CONTEXT – Weather (ECMWF)
*Last updated: 18 Oct 2026 (evening)*

## Where we are
| Step (PLAN.md) | Status |
|---|---|
| 1 Downloader – IFS, AIFS, ensemble | **Built and tested 18 Oct** (not in an app yet) |
| 2 Seasonal (Copernicus) | **Built and tested 18 Oct** – Oct 2026 forecast (Oct–Mar), 51 members, matches ECMWF's own average |
| 3 Refresh | **Manual only (user, 18 Oct)**: Claude runs `run_download.py --update` when asked. No automatic downloads for now |
| 4 App shell at http://127.0.0.1:8892 | **Built 18 Oct** – runs from source (`weather.py`), reads `data\` only |
| 5 Tabs: Short / Medium / AI vs IFS / Seasonal / Map | **Built 18 Oct** – waiting for user review |
| 6 BOM correction (learn each city's usual error) | **Recording started 18 Oct** (W-008a). Correction (W-008b) from ~mid Nov, once 2–4 weeks of forecast + actual pairs exist |
| 7 Package .exe | **Released 20 Oct** – `2. Output\Weather.zip` (73 MB). Tested from a clean folder: window opens maximised,
  BOM refresh and a 15 MB ECMWF test inside the exe OK. Full refresh not yet run from the exe (user tests tonight at home) |

## Data feeds (details in PLAN.md)
- **IFS** main model: 00z/12z to 15 days (3-hourly to day 6, then 6-hourly); 06z/18z to 90 h.
- **AIFS** AI model: 00z/12z, 6-hourly to 15 days. No max/min temperature. Rain in mm (IFS in metres).
- **Ensemble**: 00z, 50 runs, temp + max/min, 100 m wind, rain, solar. **14.9 GB per run, ~20 min** (keeps 21 MB map + 230 KB cities).
- **Seasonal** ECMWF SEAS5 + BOM ACCESS-S2: monthly, area cut on Copernicus' server (tiny).
- **BOM city forecasts** (FTP XML, 7 days, every issue kept in `data\cities\bom`).
- **BOM observations** (`backend\obs.py`, W-008a): daily records from 1 Sep 2026 + half-hourly, `data\obs\`, on every
  refresh. BOM needs a browser-like User-Agent. Adelaide daily file is IDCJDW5081 (West Terrace).
- Source: AWS copy of ECMWF open data (3.5× faster), ECMWF server as backup. ECMWF keeps ~4 days.

## What we learned
- ECMWF files are whole-globe only; no area option on the free server. Copernicus does cut the area.
- Per field per time step ≈ 0.6–1.4 MB per ensemble member → full ensemble is heavy; we fetch only fields we need.
- Coastal grid squares read 2–3 °C too cool (part sea). Cities use the nearest ≥ 90% land square; Adelaide set by
  hand to −34.75, 138.75 (nearest land square is in the Adelaide Hills).
- Values are 25 km-square averages, not station values. Remaining gap vs BOM (days 1–5): highs −0.5 °C avg,
  lows −1.0 °C avg; Brisbane highs and Sydney/Hobart lows ~2 °C cool → BOM correction (step 6).
- IFS 15-day run 808 MB / ~4 min; AIFS 501 MB / ~3 min. Daily total ≈ 17–18 GB of internet, ~60 MB kept per day.
- Seasonal: Copernicus queues each request (first try ~1–5 min per field; repeats are cached, seconds).
  Solar file says "J m**-2" but is really W/m²; each month is dated at its END (1 Nov = October) – both handled.
- Test runs (`--max-steps`) write `*_testN` files and never touch the real run (bug fixed 18 Oct).

## Refresh rule (18 Oct)
- Only when the user asks ("refresh"). Full refresh ≈ 18 GB internet (home OK, office not). Global data is never saved – only the east coast.

## Open items
- [x] Full test of all three feeds, 18 Oct 00z run – all in `data\catalog.json`.
- [x] Step 2 seasonal downloader (18 Oct).
- [x] Step 4–5 app at http://127.0.0.1:8892 (18 Oct). Choices: fixed layouts, all 5 regions side by side,
  NEM time (AEST), charts + daily table. Screenshots in `2. Output\screenshots` (light + dark), no page errors.
- [ ] User review of the screen → changes.
- [x] 20 Oct: W-015 editable screen (pages + Edit mode like NEM Trader, region / field picker per panel, ⓘ from
  cards, G2 retired – map controls inside G1) and W-016 download % (header + A1). Tests: e2e_pages 15 checks ×2
  themes, e2e_edit 18 checks, no page errors.
- Keep (user, 20 Oct): **city data forever** (forecasts every run, BOM, observations, seasonal – ~130 MB/year);
  **maps 30 days** (~1.8 GB). Already how it works (`GRID_KEEP_DAYS = 30`).
- Weather.exe: one screen, one window (user, 20 Oct). The exe will do the downloading; at 10 Mbit/s a full
  refresh (~18 GB) ≈ 4 h, the 7 am refresh (~1.3 GB) ≈ 18 min. Suggested routine: ~7 pm (with ensemble) and ~7 am.
- [x] 18 Oct evening: rule – every panel has a card (`4. Docs\panels\`), BACKLOG (W-numbers) and MODELS.md started.
- [x] W-005 Short: ensemble band + AIFS line + rain chance. W-006 BOM city forecasts on Short / Medium (▲▼ + BOM column).
  W-007 BOM ACCESS-S2 seasonal beside ECMWF (110 runs). All built 18 Oct, no page errors.
- Region order on every tab (user, 18 Oct): NSW, QLD, VIC (top row) · SA, TAS (bottom row) – `ORDER` in `web/app.js`.
- Refresh fetches the **newest run only** (user, 18 Oct) – `BACKFILL_HOURS` all 0 in `backend/ecmwf.py`.
  (Older IFS runs 17 Oct 06z/12z/18z were already fetched before the change – kept, useful for the correction.)
- [x] 20 Oct: W-017 compare runs (run + vs pickers on S1 / M1 / L1 / G1, dashed older run, Change columns, change map,
  D1 "What changed") – e2e_runs 10 checks OK on the 4 IFS runs on disk; M1 / L1 need a 2nd run (refresh) to show it.
- [x] 20 Oct: W-018 Refresh button (Full / Without ensemble / BOM only) + Weather.exe released (one window).
  Copernicus key: `.cdsapirc` next to Weather.exe (or in the user folder) – without it seasonal is skipped, rest works.
- [ ] Tonight (user, home internet): install the zip, Refresh → Full, watch the % – then check Medium / Seasonal / D1.
- 20 Oct: user chose option B – Weather.zip goes to the trading PC now; the trading PC may download ECMWF for testing
  (first "Without ensemble" ~1.5 GB, then "Full" if the office line allows). Copy `.cdsapirc` next to Weather.exe there.
  If problems: ask for `data\weather.log` + a screenshot.
- 20 Oct: W-019 cloud refresh – GitHub project nem-weather (public) created, code pushed, Copernicus key as secret,
  first jobs by hand: light 4 min (IFS + AIFS + BOM), seasonal 2 min (after fixing a hidden character in the key),
  full (ensemble) running. New Weather.zip (20 Oct, evening) fills itself from the cloud ~20 s after start, then hourly.
  Scheduled jobs: 21:30 UTC (7:30 am NEM, light) and 10:00 UTC (8 pm NEM, full).
- Backlog for later (user, 18 Oct): W-009 AIFS ENS, W-010 NOAA GFS/GEFS, W-011 other seasonal centres.
- First look: BOM's Brisbane highs sit 2–3 °C above the whole ECMWF ensemble range (ECMWF too cool there →
  W-008 BOM correction). BOM ACCESS-S2 leans warmer than ECMWF SEAS5 (e.g. Sydney Oct +1.8 vs +1.0 °C).

## The screen (18 Oct)
- Header: tabs + field picker (Temperature / Wind 100 m / Solar / Rain) + run times (red if > 30 h old) + Theme.
- Region tabs: 3×2 grid = QLD, NSW, VIC, SA, TAS panels (chart + daily table) + "About this page" (notes + runs).
  - Short: IFS 0–72 h; solar shows cloud % dashed; solar/rain drawn at the middle of each 3 h period.
  - Medium: ensemble 10–90% band + middle + IFS + AIFS lines; rain/solar as daily bars + whiskers; table "mid (range)" + rain chance.
  - AI vs IFS: two lines / daily bars; table IFS / AIFS, yellow = big difference.
  - Seasonal: monthly bars vs normal + 10–90% whiskers; table with "chance warmer/wetter…" (yellow ≥ 70% or ≤ 30%).
- Map: east-coast heatmap (IFS / AIFS / ensemble middle / seasonal), coastline from ECMWF land-sea mask
  (`data\static\lsm.npz`, saved by the downloader), time slider starting at "now".
