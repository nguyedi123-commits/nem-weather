# SKILL – How to work on Weather (ECMWF)

All commands run from `3. Code\weather\` using the project venv `..\..\.venv`. **What** we build is in PLAN.md;
this file is **how**.

## Python
```
py -3.14 -m venv .venv                     (from the project root)
.venv\Scripts\pip install ecmwf-opendata xarray cfgrib eccodes pandas pyarrow cdsapi requests playwright
```
- `eccodes` (the ECMWF file reader) ships its own binary for Windows – no separate install.
- A venv can't be moved: recreate it if the folder moves.

## Keys
- Copernicus: `C:\Users\nguye\.cdsapirc` (`url: https://cds.climate.copernicus.eu/api` + `key: ...`). Never paste the
  key in chat or in code. Licence accepted for `seasonal-postprocessed-single-levels`; other seasonal datasets may
  need their own licence click (error says "required licences not accepted" + a link).
- ECMWF open data: no key.

## Downloader – `backend\ecmwf.py`, settings `backend\config.py`
```
..\..\.venv\Scripts\python run_download.py --update                   catch up all feeds (what the app will do)
..\..\.venv\Scripts\python run_download.py --feed ifs                 latest run of one feed (ifs | aifs | ens)
..\..\.venv\Scripts\python run_download.py --feed ens --max-steps 3   quick test → files named *_test3
```
- How it works: read the file's `.index` → byte-range only the fields we need → decode in memory (eccodes) →
  keep the east-coast box + 5 city squares → `data\work\<feed>\<run>\sNNN.npz` per step → when all steps are in,
  combine to `data\cities\<feed>\<run>.parquet` + `data\grid\<feed>\<run>.npz`, add to `data\catalog.json`, delete work.
- Change places / area / feeds / steps / fields in `config.py` (`CITIES`, `CITY_SQUARE`, `GRID`, `FEEDS`, `MAXMIN`).
- Units: read from each file (`_scale`); rain and solar are "total since run start" → per-period (`_per_period`).
- Output units: °C, km/h, %, mm per period, W/m² average over period. Times stored in UTC; show in AEST (UTC+10).
- `DownloadLock` stops two downloaders running at once. Log: `data\download.log`.
- Files on the ECMWF server: `{date}/{HH}z/{ifs|aifs-single}/0p25/{oper|enfo}/{date}{HH}0000-{step}h-{oper-fc|enfo-ef}.grib2`
  (+ `.index`). Max/min temp: `mx2t3`/`mn2t3` to 144 h, `mx2t6`/`mn2t6` after.

- Seasonal only: `run_download.py --seasonal` (`backend\seasonal.py`) – ECMWF SEAS5 (feed `seasonal`) + BOM
  ACCESS-S2 (feed `seasonal_bom`), both from Copernicus. Each request queues 1–5 min.
- BOM only: `run_download.py --bom` = city forecasts (`backend\bom.py`, FTP XML) + observations (`backend\obs.py`), seconds.
- Refresh = `--update` = BOM forecasts + BOM observations + all ECMWF feeds + seasonal. **Only when the user asks** (~18 GB).

## Docs rule
- Every panel has a card in `4. Docs\panels\` (index `4. Docs\README.md`, requests `4. Docs\BACKLOG.md`, models
  `4. Docs\MODELS.md`). Change a panel → update its card (and change log) first, then code.

## Checking data against BOM
- BOM city forecasts (XML, FTP): `ftp://ftp.bom.gov.au/anon/gen/fwo/` – IDQ11295 (QLD), IDN11060 (NSW),
  IDV10753 (VIC), IDS10044 (SA), IDT16710 (TAS). Area `description` = city name, `type="location"`.
- Compare daily max/min by local day; max/min values cover the 3 h (or 6 h) *before* their time.

## Run the app (dev copy)
```
..\..\.venv\Scripts\python weather.py --browser --port 8892      dev: server only, open http://127.0.0.1:8892
..\..\.venv\Scripts\python weather.py                             the program window (as Weather.exe)
..\..\.venv\Scripts\python tests\e2e_pages.py http://127.0.0.1:8892 "..\..\2. Output\screenshots" [light|dark]
..\..\.venv\Scripts\python tests\e2e_edit.py http://127.0.0.1:8892 "..\..\2. Output\screenshots"
..\..\.venv\Scripts\python tests\e2e_runs.py http://127.0.0.1:8892 "..\..\2. Output\screenshots"   (W-017 compare runs)
..\..\.venv\Scripts\python tools\build_help.py      after changing a card: rebuilds web\help.json (the ⓘ text)
```
- NEM Trader is on 8890, Nem Watch 8891. Look copied from NEM Trader (`web\app.css` colours, ECharts 6.1 in `web\vendor\`).
- Files:
  - `backend\views.py` – data → JSON per source (short / medium / compare / seasonal / map), no downloads.
  - `backend\server.py` – http, cache (rebuilt when `data\catalog.json` changes), pages `/api/layout/<page>`
    (GET / PUT / DELETE), `/api/layouts`, `/api/settings`, `/api/status` (+ download progress).
  - `backend\progress.py` – the downloader writes `data\progress.json`; > 10 min without news = "stopped".
  - `web\app.js` – grid (GridStack 24 × 36), pages, Edit mode, dialogs, status (copied from NEM Trader's app.js).
  - `web\panels.js` – panel kinds `PANELS` (code, title, source, pickers, create) + all chart code.
  - `web\layouts\<page>.json` – built-in pages (Reset); saved pages in `settings\layouts\`.
- New panel: card first → `PANELS` entry in `web\panels.js` (+ data in `views.py` / route in `server.py` if new)
  → code in `tools\build_help.py` KIND → rebuild help → tests.
- `backend\` changes need a server restart; `web\` changes only a page reload.
- The page polls `/api/status` every 60 s and redraws when a refresh has added data.
- e2e tests (Playwright + Edge): `e2e_pages` = every built-in page, field / model pickers, ⓘ, screenshots;
  `e2e_edit` = Edit mode like a user (add / pick / drag / resize / A+ / minimise / remove, page add / copy / rename /
  delete / reset) and checks what was saved. Both clean up after themselves.
- When stopping processes: check the command line first (`weather.py`) – NEM Trader's dev server is also `python.exe`.

## Release (only when the user says "release") – first release 20 Oct
```
build\build.bat                                     rebuilds web\help.json, then PyInstaller -> build\dist\Weather\
..\..\.venv\Scripts\python build\make_zip.py     -> 2. Output\Weather.zip + Weather (update).zip
```
- Recipe: `build\weather.spec` (copied from NEM Trader; bundles web\, pywebview + .NET, eccodes DLLs, cdsapi).
  Icon: `build\make_icon.py`. Notes in the zip: `build\READ ME - install.txt` / `update.txt`.
- Test before handing over: unzip into an EMPTY folder, start Weather.exe, then (server port in data\weather.log,
  8893 if the dev copy has 8892):  POST /api/refresh {"mode":"bom"}  and  {"mode":"test"} (2 IFS steps, ~15 MB, files *_test2,
  proves eccodes works inside the exe). Close it, delete the folder.
- Screenshots of the real window: PowerShell must call SetProcessDPIAware first (this PC is scaled 125 %), else the
  picture is cut off.
- The exe: one window (maximised), data\ + settings\ next to Weather.exe (or %LOCALAPPDATA%\Weather if not writable),
  log data\weather.log, next free port from 8892, only one copy at a time.
