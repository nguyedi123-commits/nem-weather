# Weather.exe – ECMWF forecasts for the NEM trading screens

## Context
- Traders need east-coast weather (QLD, NSW, VIC, SA, TAS) for demand and wind/solar: short (0–3 d), medium (to 15 d), seasonal (to 6 months).
- Source: ECMWF free open data (CC BY 4.0, must credit ECMWF) + Copernicus seasonal (SEAS5).
- Weather.exe is new, built the same way as NEM Trader (`21) NEM Screens\6. NEM Trader`): Python + local web page in a pywebview window, ECharts, same colours/tabs.

## Decisions so far (18 Oct 2026)
- Locations: Brisbane, Sydney, Melbourne, Adelaide, Hobart **+ east-coast grid** (lat −9…−44, lon 129…155, 0.25°) for maps.
- Fields: temperature (+ true daily max/min), dew point, 10 m + 100 m wind (speed + direction), solar radiation, cloud, rain.
- Horizons: Short, Medium (with ensemble range), Seasonal, AI-model comparison.
- **Refresh manually, only when you ask** (18 Oct): ~18 GB per full refresh, home internet only. ECMWF keeps ~4 days of runs, so a refresh still picks up missed runs. Automatic refresh parked.
- **Disk kept small**: global data never saved – only the east coast is kept.
- Free ECMWF server has no area option (whole-globe files only) → we fetch only needed fields, cut the east coast locally. Copernicus seasonal *does* cut the area on the server (~12 KB per field).
- Stand-alone app (weather only); NEM Trader code is copied in, not shared.
- Download from the AWS copy of ECMWF open data (3.5× faster), ECMWF server as fallback.
- Times shown in NEM time (AEST, UTC+10, no daylight saving).

## Data feeds

| Feed | Runs | Range / steps | Fields | Download / day |
|---|---|---|---|---|
| IFS main model | 00z, 12z | 3-hourly to 6 d, 6-hourly to 15 d | all + max/min | ~1.4 GB (0.7 per run) |
| IFS main model | 06z, 18z | 3-hourly to 90 h | all + max/min | ~0.5 GB |
| AIFS (AI model) | 00z, 12z | 6-hourly to 15 d | all (no max/min in AIFS) | ~0.8 GB (0.4 per run) |
| IFS ensemble (50 runs) | 00z | 6-hourly to 7 d, then 4 pm / 4 am AEST to 15 d | temp + max/min, 100 m wind, solar, rain | ~15 GB (measured) |
| SEAS5 seasonal | monthly (~5th) | months 1–6 | temp, rain, wind, solar anomalies | tiny (server cuts the area, 1° grid) |

Kept on disk (`data\`):
- `cities\<feed>\<run>.parquet` – every run, kept forever (IFS ~30 KB/run, ensemble ~1 MB/run).
- `grid\<feed>\<run>.npz` – map data, last 30 days (IFS ~11 MB/run).
- `catalog.json` – finished runs. `work\` – unfinished steps (resume), deleted when a run completes.
- City squares: nearest 0.25° square that is ≥ 90% land (coastal squares read 2–3 °C too cool). Adelaide set by hand to −34.75, 138.75 (nearest land square is in the cooler hills). Set in `backend\config.py`.
- Ensemble: p10 / median / p90 + mean for cities and grid; all members for cities only.
- Rain and solar: converted from "total since run start" to per-period amounts (mm, W/m²).

## Build steps
1. **Downloader** (`3. Code\weather\backend\ecmwf.py`)
   - Reads each file's index and fetches only the fields needed (byte ranges), 3 steps × 4 connections.
   - Global data is decoded in memory and never saved; only the east coast is kept.
   - Units read from each file (AIFS rain is mm, IFS rain is metres).
   - Resumes from the last finished step if the PC is turned off.
   - Lock so two copies never download at once.
   - Command line: `3. Code\weather\run_download.py --update` (or `--feed ifs|aifs|ens [--max-steps N]`).
   - **Status 18 Oct: built and tested** (see Test results).
2. **Seasonal** (`backend\seasonal.py`): Copernicus API (`cdsapi`, key in `C:\Users\nguye\.cdsapirc`), area-cut request; fetched on refresh when a new month is out (5th of the month).
   - Fields (difference from normal): temperature °C, rain mm/day, 10 m wind km/h, solar W/m². All 51 members.
   - Saved: `cities\seasonal\<YYYYMM>.parquet` (members) + `grid\seasonal\<YYYYMM>.npz` (mean, p10, p90, chance above normal).
   - **Status 18 Oct: built and tested** – values match ECMWF's published ensemble average.
3. **Refresh – manual for now** (18 Oct)
   - Claude runs `run_download.py --update` when you ask; the app only reads `data\` and shows how old each run is.
   - Automatic refresh (on start / every 15 min) parked until you ask for it.
4. **App**:
   - Copy the NEM Trader shell (`trading_screen.py` windows, `backend\server.py` local server, `web\app.js` tabs, `web\app.css` colours, `web\panels\common.js` charts, `web\vendor`).
   - Dev: run from source and open http://127.0.0.1:8892 in the browser (like NEM Trader on 8890). No exe until "release".
   - **Status 18 Oct: built** (steps 4 + 5) – fixed layouts, all 5 regions side by side, NEM time, charts + daily tables. Waiting for your review.
5. **Tabs and panels**

   | Tab | Panels |
   |---|---|
   | Short | 0–3 days, one panel per region: temp, wind, solar, rain lines (IFS) |
   | Medium | 15 days: ensemble band (p10–p90) with IFS and AIFS lines; daily max/min temp table |
   | AI vs IFS | The two models side by side, plus the difference |
   | Seasonal | Monthly anomaly bars per region ("warmer / drier than normal"), plus a map |
   | Map | East-coast heatmap (temp, wind, solar, rain), time slider, model picker |

   - Status bar: latest run per feed, next update, download progress, "Data: ECMWF CC BY 4.0".
6. **BOM correction** (agreed 18 Oct)
   - Record BOM observations for the 5 cities (BOM JSON feeds, same as NEM Trader's `get_weather()`), kept as history.
   - After ~2–4 weeks: learn each city's usual error by time of day and lead time (e.g. "Sydney lows run 2 °C cool").
   - Show "ECMWF corrected" next to raw ECMWF; keep raw values on disk.
   - BOM data will also be used elsewhere later.
7. **Package**: PyInstaller one-folder, copying NEM Trader's `build\build.bat`, `trading_screen.spec` and `make_zip.py`.
   - Zips: `2. Output\Weather.zip` (first install) and `Weather (update).zip`.
   - Built only when you say "release".

## Cloud refresh (W-019, agreed 20 Oct)
- GitHub public project `nem-weather` (code + docs only; never data, settings or the key).
- GitHub job (Actions) at 7 am NEM (21:00 UTC, without ensemble) and 7 pm NEM (09:00 UTC, full) + a "run now" button:
  runs `run_download.py` on GitHub's computer, keeps only the NEM east coast, publishes each new run as a small
  download (GitHub "release" files, ~60 MB per run) + a list of what's there; deletes cloud copies older than 30 days.
- Copernicus key stored as a GitHub secret (hidden, not in the public code).
- Weather.exe: every hour reads the list (tiny), downloads only runs it doesn't have, unpacks into data\. History is
  kept on the trading PC as before (cities forever, maps 30 days). Refresh button: "From the cloud" first; direct
  ECMWF download stays as back-up.
- Free: GitHub minutes don't count downloads; public projects have no minute limit (private: ~1,080 of 2,000/month).

## Testing (locally, before any release)
- Downloader: one run per feed. Compare city values with BOM forecasts for the same day.
- Check rain/solar per-period maths and that times are in AEST.
- Turn-off test: kill mid-download, restart, confirm it resumes.
- Disk test: raw folder empty after each run.
- Screenshots of every tab → `2. Output\screenshots`.
- Exe test on a clean folder; check the bundled ECMWF file reader (eccodes) works inside the exe.

## Test results – step 1 (18 Oct 2026, 00z run)
- Speed: IFS 15-day run 700 MB in ~4 min; AIFS 405 MB in ~2 min; ensemble ~9 MB/s.
- Kill mid-download → restart resumed ("12 already done"), work folder empty after finish.
- Lock: second downloader blocked.
- vs BOM city forecasts, days 1–5: max temp avg −0.5 °C (avg miss 1.6 °C), min temp avg −1.0 °C (avg miss 1.5 °C).
  - Brisbane highs ~2 °C cool; Sydney/Hobart lows ~2–2.5 °C cool – normal for a raw model.
  - Fix: BOM correction (step 6).

## Open items (need you)
- [x] Copernicus licence accepted – seasonal test download OK (18 Oct).
- [x] Plan confirmed: rain in ensemble, stand-alone app, tabs Short / Medium / AI vs IFS / Seasonal / Map.
- [x] Copernicus API key replaced, new key tested OK (18 Oct).
- [x] Dev copy at http://127.0.0.1:8892; no exe yet.
- [x] BOM correction added as step 6.
