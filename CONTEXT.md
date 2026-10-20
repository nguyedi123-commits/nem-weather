# CONTEXT – Weather (ECMWF)
*Last updated: 20 Oct 2026 (night)*

## In one line
Weather.exe (one window) shows ECMWF + BOM forecasts for the NEM east coast. A **GitHub cloud job** downloads twice a
day and keeps only the NEM region; Weather.exe picks the small files up **every hour by itself**.

## Where we are
| Part | Status |
|---|---|
| Downloader – IFS, AIFS, ensemble, BOM forecasts + observations, seasonal (ECMWF + BOM) | Built, tested |
| Screen – pages Short / Medium / AI vs IFS / Seasonal / Map, Edit mode, region + field + run / vs pickers, ⓘ | Built, tested (W-015, W-017) |
| Cloud – GitHub job + hourly pick-up (W-019, W-012) | **Built 20 Oct.** By-hand jobs all green; first scheduled runs 21 Oct |
| Weather.exe | **New zip 20 Oct night** (`2. Output\Weather.zip` / `(update).zip`, 73 MB) – fills itself from the cloud ~20 s after start |
| I1 Insights panel (W-021) – plain-words headlines + what changed, NSW/QLD/VIC/SA, on each page where TAS was | **Built 20 Oct night**, in the new zip |
| Ensemble full-day max/min (W-022, feed `ensx`) + map Play button (W-023) | **Built 20 Oct night**, cloud job OK, in the new zip |
| BOM correction (W-008b) | Recording observations since 18 Oct (history from 1 Sep). Correction from ~mid Nov |

## Next (21 Oct)
- [ ] User puts the NEW Weather.zip on the trading PC (cloud pick-up). Old zip from 20 Oct morning had no cloud.
- [ ] 21 Oct: the 7:30 am scheduled job never started (GitHub late on round times) → light job run by hand 8:01 am (OK,
  IFS + AIFS 20 Oct 22:00 run). Times moved to **7:37 am / 8:07 pm NEM**. Check tonight's 8:07 pm job starts by itself.
- [ ] Check the trading PC picked them up (About panel: "Cloud last made data" / "This PC last checked").
- [ ] User review of the screen → changes.
- Later: W-020 keep the GitHub schedule alive (monthly upload, due before ~19 Dec), W-008b BOM correction (~mid Nov),
  W-014 forecast-check panel, backlog W-009 AIFS ENS / W-010 NOAA / W-011 other seasonal centres.

## Cloud facts (20 Oct)
- Project https://github.com/nguyedi123-commits/nem-weather (public, code + docs only). Copernicus key = hidden secret.
- Job times: light ~4 min, seasonal ~2 min, full (ensemble 14.9 GB) **~14 min**. ~18 min/day; public = no minute limit.
- Published per day ≈ 45 MB (IFS 13.6, AIFS 7.9, ensemble 21.0 MB + BOM, seasonal, obs). Cloud keeps 30 days (seasonal 400).
- BOM's servers work from GitHub's computers. Scheduled jobs can start 5–30 min late (harmless).
- GitHub turns schedules off after 60 days without code uploads → W-020.
- First by-hand job failed: a hidden character (byte-order mark) on the key from PowerShell piping – fixed (`--body`
  + the job strips it).

## User decisions (keep)
- Pages (user, 20 Oct): TAS removed everywhere – NSW, QLD, About (top) · SA, VIC, I1 Insights (bottom).
  Built-in pages match. Insights cover NSW, QLD, VIC, SA (rules in card I1). Times: NEM time (AEST). Charts + daily table.
- Keep **city data forever**, **maps 30 days**. Newest run only on direct downloads (`BACKFILL_HOURS` 0).
- One screen, one window (no multi-monitor). Every panel has a card in `4. Docs\panels\` (card first, then code).
- No .exe / zip until the user says "release" (released 20 Oct, twice).
- This PC: direct ECMWF download only when asked (~18 GB); the cloud is now the normal way.

## Data feeds
- **IFS** main model: 00z/12z to 15 days (3-hourly to day 6, then 6-hourly); 06z/18z to 90 h.
- **AIFS** AI model: 00z/12z, 6-hourly to 15 days. No max/min temperature. Rain in mm (IFS in metres).
- **Ensemble**: 00z, 50 runs, temp + max/min, 100 m wind, rain, solar. 14.9 GB download → 21 MB kept.
- **Seasonal** ECMWF SEAS5 (51 runs, 5th of the month) + BOM ACCESS-S2 (110 runs, by the 10th), Copernicus.
- **BOM city forecasts** (FTP XML, 7 days) and **observations** (daily records + half-hourly), every issue kept.
- Source: AWS copy of ECMWF open data, ECMWF server as back-up. ECMWF keeps ~4 days of runs.

## What we learned
- ECMWF's free files are whole-globe only; we fetch only needed fields and cut the east coast in memory.
- Coastal grid squares read 2–3 °C too cool → cities use the nearest ≥ 90 % land square (Adelaide set by hand).
- Raw ECMWF vs BOM (days 1–5): highs −0.5 °C, lows −1.0 °C on average; Brisbane highs, Sydney / Hobart lows ~2 °C cool.
- BOM ACCESS-S2 leans warmer than ECMWF SEAS5 (Sydney Oct +1.8 vs +1.0 °C).
- First ensemble comparison (20 Oct vs 18 Oct): 24 notable changes, e.g. NSW Wed rain chance 20 → 86 %.
- This PC: full direct refresh ~26 min (~12 MB/s). GitHub's computer ~3× faster.
