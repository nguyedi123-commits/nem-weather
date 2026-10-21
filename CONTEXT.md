# CONTEXT – Weather (ECMWF)
*Last updated: 22 Oct 2026 (~1 am Sydney)*

## In one line
Weather.exe (one window) shows ECMWF + BOM forecasts for the NEM east coast. A **GitHub cloud job** downloads twice a
day and keeps only the NEM region; Weather.exe picks the small files up **by itself** (now every 15 min – new exe pending).

## Where we are
| Part | Status |
|---|---|
| Downloader – IFS, AIFS, ensemble (+ `ensx` full-day max/min), BOM forecasts + observations, seasonal (ECMWF + BOM + **CFS US**, W-011a) | Built, tested (CFS 21 Oct) |
| Screen – pages Short / Medium / AI vs IFS / Seasonal / Map, Edit mode, region + field + run / vs pickers, ⓘ, I1 Insights, map Play | Built, tested |
| Cloud – GitHub job + pick-up (W-019, W-012, W-024) | Built 20 Oct. **GitHub's timer has never fired** → this PC starts the jobs (Task Scheduler, see Next) |
| Weather.exe | Latest zip **21 Oct 09:48** (`2. Output\Weather.zip`, 70 MB) – trusts Windows certificates. **Not yet in an exe: CFS, 15-min pick-up** (needs "release") |
| Trading PC | **21 Oct: installed and working** (on a non-office Wi-Fi – see below) |
| BOM correction (W-008b) | Recording observations since 18 Oct (history from 1 Sep). Correction from ~mid Nov |

## Trading PC install (21 Oct)
1. Copy `2. Output\Weather.zip` to the trading PC.
2. Unzip to a writable folder, e.g. `C:\Weather` (not Program Files).
3. Start `C:\Weather\Weather\Weather.exe` (SmartScreen: More info → Run anyway – unsigned program).
4. Wait ~20 s: it fetches ~40 MB from the cloud by itself.
5. Check: About panel shows "Cloud last made data 21 Oct 08:05" + "This PC last checked" (today); Short page has
   NSW / QLD / SA / VIC charts + Insights.
6. Optional: shortcut to Weather.exe in `shell:startup` to start with Windows.
- If problems: ask for `C:\Weather\Weather\data\weather.log` + a screenshot.

## Next
- [x] Trading PC working (21 Oct). The **office Wi-Fi** FortiGate firewall inspects github.com with a certificate
  the PC doesn't trust → "Cloud not reachable". User uses another Wi-Fi. If needed later: IT installs the Fortinet
  certificate (no rebuild – the exe uses Windows' certificates) or Weather.exe fetches from GitHub's file storage instead.
  Check tool: `2. Output\Weather net check\RUN ME.bat`.
- [ ] **W-024 data by 8 am Sydney** (user, 21 Oct). Measured: ECMWF IFS + AIFS overnight (12z) run complete 19:34 UTC =
  6:34 am Sydney every day; BOM morning issues QLD ~4:50, SA ~5:45, NSW ~7:20, TAS ~8:15, VIC ~8:40 am; ensemble 7 pm.
  Done: cloud light jobs 19:52 + 20:22 UTC (6:52 / 7:22 am Sydney), full 10:07 UTC (9:07 pm); seasonal only in the
  evening job and published after the forecasts; job limit 330 min; Weather.exe checks every 15 min (in code, **exe
  not built** – ask for "release").
- [ ] **GitHub's timer never fired** (21 Oct morning + evening, 0 scheduled runs; workflow active, Actions on). Back-up
  on THIS PC: Task Scheduler "Weather cloud morning 1 / morning 2 / evening" → `tools\cloud_trigger.ps1`
  (log `data\cloud_trigger.log`). Only works while this PC is on (wakes it from sleep). Check 22 Oct ~7:30 am:
  `gh run list` – which jobs ran (schedule vs workflow_dispatch)? If GitHub's timer stays dead: an always-on trigger.
- [x] 21 Oct evening job missed → run by hand 13:48 UTC (BOM test + full).
- [ ] CFS (W-011a) built + tested on the dev copy (L1 third bar + table, I1 "CFS agrees", map "Seasonal CFS (US)").
  User to look at it. CFS solar leans much sunnier than ECMWF / BOM (noted in L1 Limits).
- [ ] User review of the screen → changes. Offered: daily high / low range markers on the Medium chart (days 8–15).
- Later: W-020 keep the GitHub schedule alive (monthly upload, due before ~19 Dec), W-008b BOM correction (~mid Nov),
  W-014 forecast-check panel, backlog W-009 AIFS ENS / W-010 NOAA GFS (user: not wanted – poor) / W-011 other seasonal centres.

## Cloud facts
- Project https://github.com/nguyedi123-commits/nem-weather (public, code + docs only). Copernicus key = hidden secret.
- Job times: light ~4 min, seasonal 2 min to **4.5 h** (Copernicus queue, 21 Oct), full (ensemble 14.9 GB + `ensx` 2.6 GB) ~16 min. Public = no minute limit.
- Published per day ≈ 45 MB (IFS 13.6, AIFS 7.9, ensemble 21.0 MB, `ensx` 48 KB + BOM, seasonal, obs).
  Cloud keeps 30 days (seasonal 400).
- BOM's servers work from GitHub's computers. Scheduled jobs can start late or be skipped at busy round times.
- GitHub turns schedules off after 60 days without code uploads → W-020.
- 20 Oct: first by-hand job failed (hidden byte-order mark on the key from a PowerShell pipe – fixed); a later one
  failed on a missing `BACKFILL_HOURS` entry for `ensx` (fixed).

## User decisions (keep)
- Pages: TAS removed everywhere – NSW, QLD, About (top) · SA, VIC, I1 Insights (bottom). Built-in pages match.
  Insights cover NSW, QLD, VIC, SA (rules in card I1). Times: NEM time (AEST). Charts + daily table.
- Keep **city data forever**, **maps 30 days**. Newest run only on direct downloads (`BACKFILL_HOURS` 0).
- Ensemble max/min over all 24 hours via extra max/min-only steps (option B, W-022).
- One screen, one window (no multi-monitor). Every panel has a card in `4. Docs\panels\` (card first, then code).
- No .exe / zip until the user says "release". This PC: direct ECMWF download only when asked; the cloud is normal.

## Data feeds
- **IFS** main model: 00z/12z to 15 days (3-hourly to day 6, then 6-hourly); 06z/18z to 90 h.
- **AIFS** AI model: 00z/12z, 6-hourly to 15 days. No max/min temperature. Rain in mm (IFS in metres).
- **Ensemble**: 00z, 50 runs, temp + max/min, 100 m wind, rain, solar (6-hourly to day 7, then 4 am / 4 pm).
  **`ensx`**: max/min only at the missing steps → daily high / low cover all 24 hours (from 20 Oct 00z run).
- **Seasonal** ECMWF SEAS5 (51 runs, 5th of the month) + BOM ACCESS-S2 (110 runs, by the 10th) + NCEP CFSv2 (US, 120
  runs, by the 13th), all Copernicus monthly. Long range only – CFS is too coarse for days ahead.
- **BOM city forecasts** (FTP XML, 7 days) and **observations** (daily records + half-hourly), every issue kept.
- Source: AWS copy of ECMWF open data, ECMWF server as back-up. ECMWF keeps ~4 days of runs.

## What we learned
- ECMWF's free files are whole-globe only; we fetch only needed fields and cut the east coast in memory.
- Coastal grid squares read 2–3 °C too cool → cities use the nearest ≥ 90 % land square (Adelaide set by hand).
- Raw ECMWF vs BOM (days 1–5): highs −0.5 °C, lows −1.0 °C on average; Brisbane highs, Sydney / Hobart lows ~2 °C cool.
- Ensemble part-day max/min made lows too warm: full-day (`ensx`) lowers them up to 2.6 °C (SA), highs up to +1.1 °C.
- Medium chart after day 7 has only 4 am / 4 pm points – the afternoon peak isn't drawn; table + I1 use true highs.
- BOM ACCESS-S2 leans warmer than ECMWF SEAS5 (Sydney Oct +1.8 vs +1.0 °C).
- Office Wi-Fi (FortiGate) blocks github.com only; GitHub file storage, ECMWF, BOM pass.
- Sydney summer time = UTC+11, NEM = UTC+10. GitHub cron is UTC. ECMWF publishes at fixed UTC times.
- This PC: full direct refresh ~26 min (~12 MB/s). GitHub's computer ~3× faster.
