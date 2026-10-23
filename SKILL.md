# SKILL – How to work on Weather (ECMWF)

Commands run from `3. Code\weather\` with the project venv `..\..\.venv` (git / GitHub from the project root).
**What** we build is in PLAN.md and `4. Docs\`; where we are in CONTEXT.md; this file is **how**.

## Python
```
py -3.14 -m venv .venv                     (from the project root)
.venv\Scripts\pip install eccodes pandas pyarrow requests cdsapi playwright pywebview==6.2.1 pythonnet==3.2.1 clr_loader==0.3.1 pyinstaller==6.22.3 truststore==0.10.5
```
- `eccodes` (the ECMWF file reader) ships its own Windows DLLs. A venv can't be moved: recreate it if the folder moves.
- Cloud versions are pinned in `requirements-cloud.txt` (same as the venv).

## Keys
- Copernicus: `C:\Users\nguye\.cdsapirc` (`url:` + `key:`). Never paste the key in chat or code. In the cloud it is the
  GitHub secret `CDSAPI_KEY`. Weather.exe also reads a `.cdsapirc` next to it (direct downloads only).
- ECMWF open data, BOM: no key (BOM needs a browser-like User-Agent – done in the code).

## Cloud (W-019) – the normal way data arrives
- Project https://github.com/nguyedi123-commits/nem-weather (public: code + docs only – `.gitignore` keeps out data,
  settings, zips, keys). Git identity in this repo = GitHub no-reply address (never the personal email).
- GitHub tool: `"C:\Program Files\GitHub CLI\gh.exe"` (logged in as nguyedi123-commits).
- Job `.github/workflows/refresh.yml` → `cloud/publish.py --mode light|full|bom`:
  - 19:52 UTC light = BOM + IFS + AIFS (ECMWF's 12z run is complete at 19:34 UTC) – 6:52 am Sydney summer / 5:52 winter;
  - 20:22 UTC light again = back-up if the first is skipped + later BOM issues – 7:22 am / 6:22 am;
  - 00:47 UTC light = midday IFS 18z run (to 90 h, complete 00:27 UTC) – 11:47 am / 10:47 am;
  - 08:17 UTC full = + ensemble + `ensx` (IFS / AIFS 00z complete 07:34, ensemble 08:01 UTC) – 7:17 pm / 6:17 pm.
  - ECMWF 06z (complete 12:27 UTC = 11:27 pm Sydney) is not fetched on purpose.
  - Goal (W-024): overnight data on the trading PC by 8 am Sydney. GitHub cron is UTC only – no daylight-saving change needed.
  - **GitHub's timer had not fired once by 22 Oct** → back-up on this PC: Windows Task Scheduler tasks
    "Weather cloud morning 1" (6:52 am), "morning 2" (7:22 am), "midday" (11:47 am), "evening" (7:17 pm, full) run
    `3. Code\weather\tools\cloud_trigger.ps1 <mode>` (= `gh workflow run`), log `data\cloud_trigger.log`. They wake
    the PC from sleep, not when it is off. Remove: `Unregister-ScheduledTask -TaskName "Weather cloud*"`.
  - Order inside a job: BOM → ECMWF → **publish** → seasonal (Copernicus queue, can take hours – took 4.5 h on 21 Oct)
    → publish again. Job limit 330 min. Seasonal is checked in every light / full job but only asks Copernicus when
    a new month is due: ECMWF from the 5th, BOM from the 10th, CFS from the 13th (12 UTC = 11 pm Sydney) → on the
    trading PC by ~7:15 am the next morning.
  - Off round minutes: GitHub starts :00 / :30 schedules late or skips them (the 7:30 am job on 21 Oct never ran).
- Publishes release `data`: `<feed>__<run>.zip`, `obs.zip`, `static.zip`, `manifest.json` (the list, uploaded last).
  Keeps 30 days (seasonal 400).
- **Morning check:** `gh run list` (did the scheduled job run?) and the manifest's `last_job` (time, mode, errors, new):
  ```
  gh release download data --repo nguyedi123-commits/nem-weather --pattern manifest.json --output -
  ```
  If a scheduled job didn't start: run it by hand (`-f mode=light` morning, `-f mode=full` evening).
```
gh workflow run refresh.yml --repo nguyedi123-commits/nem-weather -f mode=light      by hand (light | full | bom)
gh run list --repo nguyedi123-commits/nem-weather --limit 5                           did the jobs work?
gh run view <id> --repo nguyedi123-commits/nem-weather --log                          a job's log
gh release view data --repo nguyedi123-commits/nem-weather --json assets              what is published
gh secret set CDSAPI_KEY --repo nguyedi123-commits/nem-weather --body <key>           NOT via a PowerShell pipe (adds a hidden BOM)
```
- Weather.exe side `backend\cloud.py`: reads the manifest every 15 min (`EVERY_S`), downloads only runs it doesn't have,
  merges obs, unpacks into `data\` (only expected paths). State `data\cloud.json`. Refresh → "From the cloud".
- Publish code changes: `git add -A`, `git commit` (end with the Co-Authored-By line), `git push` – from the project root.
- GitHub turns schedules off after 60 days without code uploads (W-020).

## Direct downloader (back-up) – `backend\ecmwf.py`, settings `backend\config.py`
```
..\..\.venv\Scripts\python run_download.py --update                   everything (~18 GB) – only when the user asks
..\..\.venv\Scripts\python run_download.py --feed ifs                 newest run of one feed (ifs | aifs | ens)
..\..\.venv\Scripts\python run_download.py --feed ens --max-steps 3   quick test → files named *_test3
..\..\.venv\Scripts\python run_download.py --seasonal                 ECMWF + BOM seasonal (Copernicus, 1–5 min per request)
..\..\.venv\Scripts\python run_download.py --bom                      BOM forecasts + observations (seconds)
```
- How it works: file `.index` → byte-range only needed fields → decode in memory → keep east-coast box + 5 city squares
  → `data\work\` per step (resume) → `data\cities\<feed>\<run>.parquet` + `data\grid\<feed>\<run>.npz` + `catalog.json`.
- Feed `ensx` (W-022): ensemble max/min only at the steps `ens` lacks (`ENS_MAXMIN`), merged into the ensemble's
  daily high/low in `views._cities`. A new feed also needs an entry in `BACKFILL_HOURS` (ecmwf.py) and in the
  "full" mode of `refresh.py` and `cloud/publish.py`.
- Change places / area / feeds / steps / fields in `config.py` (`CITIES`, `CITY_SQUARE`, `GRID`, `FEEDS`, `MAXMIN`).
- Units read from each file; rain / solar "since start" → per period. Times stored UTC, shown NEM (UTC+10).
- `DownloadLock` = one downloader at a time (app, cloud pick-up, command line). Progress: `data\progress.json`.

## Run the app (dev copy)
```
..\..\.venv\Scripts\python weather.py --browser --port 8892      server only → http://127.0.0.1:8892 (also picks up the cloud every 15 min)
..\..\.venv\Scripts\python weather.py                             the program window (as Weather.exe)
..\..\.venv\Scripts\python tests\e2e_pages.py http://127.0.0.1:8892 "..\..\2. Output\screenshots" [light|dark]
..\..\.venv\Scripts\python tests\e2e_edit.py http://127.0.0.1:8892 "..\..\2. Output\screenshots"
..\..\.venv\Scripts\python tests\e2e_runs.py http://127.0.0.1:8892 "..\..\2. Output\screenshots"
..\..\.venv\Scripts\python tools\build_help.py      after changing a card: rebuilds web\help.json (the ⓘ text)
```
- NEM Trader is on 8890, Nem Watch 8891. `backend\` changes need a server restart; `web\` changes only a reload.
- Files: `backend\views.py` (data → JSON, run / vs), `server.py` (http, cache, pages, settings, status, `/api/refresh`),
  `refresh.py` (Refresh button: cloud / full / light / bom / test), `cloud.py`, `progress.py`, `system.py` (Windows bits);
  `web\app.js` (grid, pages, Edit mode, pickers), `web\panels.js` (`PANELS` + charts), `web\layouts\` (built-in pages).
- New panel: card first → `PANELS` entry → data in `views.py` / route in `server.py` if new → `KIND` in
  `tools\build_help.py` → rebuild help → tests.
- Stopping processes: check the command line first (`weather.py`) – NEM Trader's dev server is also `python.exe`.

## Docs rule
- Every panel has a card in `4. Docs\panels\` (index `4. Docs\README.md`, requests `4. Docs\BACKLOG.md` W-numbers,
  models `4. Docs\MODELS.md`). Change a panel → card (and change log) first, then code.

## Release (only when the user says "release")
```
build\build.bat                                     rebuilds web\help.json, then PyInstaller -> build\dist\Weather\
..\..\.venv\Scripts\python build\make_zip.py     -> 2. Output\Weather.zip + Weather (update).zip
```
- Recipe `build\weather.spec` (from NEM Trader). Icon `build\make_icon.py`. Notes `build\READ ME - install.txt` / `update.txt`.
- Test: unzip into an EMPTY folder, start Weather.exe → within ~20 s `data\weather.log` says "cloud: N new files"
  and the pages fill. Direct checks (port in the log, 8893 if the dev copy has 8892): POST `/api/refresh`
  `{"mode":"bom"}` and `{"mode":"test"}` (2 IFS steps, ~15 MB, proves eccodes in the exe). Close it, delete the folder.
- Screenshots of the real window: PowerShell must call SetProcessDPIAware first (this PC is scaled 125 %).
- The exe: one window (maximised), `data\` + `settings\` next to it (or `%LOCALAPPDATA%\Weather`), log
  `data\weather.log`, next free port from 8892, one copy at a time.

## Installing on the trading PC (user does this)
- Give only `2. Output\Weather.zip` (no key, no data – the cloud fills it). Unzip to e.g. `C:\Weather`, start
  `Weather\Weather.exe` (SmartScreen: More info → Run anyway). ~20 s later the About panel shows the cloud times.
- Update later: `Weather (update).zip` unzipped over the folder (keeps `data\` and `settings\`).
- Problems: ask for `data\weather.log` + a screenshot.

## Checking data against BOM
- BOM city forecast XML: `ftp://ftp.bom.gov.au/anon/gen/fwo/` IDQ11295, IDN11060, IDV10753, IDS10044, IDT16710.
- Observations: daily `bom.gov.au/climate/dwo/<YYYYMM>/text/<IDCJDW…>.<YYYYMM>.csv` (Adelaide = IDCJDW5081),
  half-hourly `bom.gov.au/fwo/<product>.json`.
- Compare daily max/min by local day; ECMWF max/min values cover the 3 h (or 6 h) *before* their time.
