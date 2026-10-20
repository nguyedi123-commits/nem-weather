# Forecast models
*Last updated: 18 Oct 2026*

All from ECMWF (European Centre for Medium-Range Weather Forecasts), free open data, licence CC BY 4.0.
ECMWF is widely rated the most accurate global forecaster for the medium range.

## What we use, by tab
| Tab | Model(s) | Runs we take | Detail |
|---|---|---|---|
| Short · 3 days | **IFS** main model (line) + **IFS ensemble** range band + **AIFS** line + **BOM** city forecast | IFS 00z/12z (+ 06z/18z to 90 h), ensemble 00z | IFS 3-hourly, band and AIFS 6-hourly |
| Medium · 15 days | **IFS ensemble** (50 runs) + IFS line + AIFS line + **BOM** city forecast (7 days) | 00z | 6-hourly to day 7, then 4 am / 4 pm |
| AI vs IFS | **IFS** vs **AIFS Single** | 00z, 12z | IFS 3-hourly, AIFS 6-hourly |
| Seasonal · 6 months | **ECMWF SEAS5** (51 runs) + **BOM ACCESS-S2** (110 runs) | monthly (ECMWF 5th, BOM by 10th) | monthly averages vs normal |
| Map | any of the above | | 0.25° (seasonal 1°) |

(00z = 10:00 NEM time, 12z = 22:00 NEM time.)

## The models
### IFS – Integrated Forecasting System ("the main model")
- ECMWF's physics model: solves the equations of the atmosphere, oceans and land on a ~9 km global grid.
- **Single run** (stream "oper", also called HRES): one best guess, to 15 days (00z/12z) or 6 days (06z/18z).
- Open data is the same forecast, shared on a 0.25° (~25 km) grid.

### IFS ensemble (ENS)
- The same IFS model run **50 times** (+1 unperturbed "control" run we do not download), each started from slightly
  different weather and with small model changes – to show how sure the forecast is.
- Narrow spread = confident; wide spread = several outcomes possible. We show the 10–90 % range (8 in 10 runs inside)
  and the middle run (median).
- Same ~9 km model as the single run. To 15 days.

- **Full-day max / min (W-022, from 21 Oct):** the ensemble's own steps cover only part of each day, so a second, small
  download (feed `ensx`) fetches just the max / min temperature at the missing steps: 3-hourly to day 6, 6-hourly to
  day 15. Every hour of every day is then covered (~2.8 GB extra per run, on GitHub's computer).

### AIFS Single – Artificial Intelligence Forecasting System ("the AI model")
- ECMWF's machine-learning model (operational since early 2025). Trained on decades of past weather (ERA5) and
  ECMWF's own analyses; starts each run from the same starting weather as IFS.
- Runs in about a minute instead of hours; scores as well as or better than IFS on many measures (e.g. storm tracks,
  large-scale temperature), but tends to be **smoother** (less extreme peaks) and has no true hourly max/min.
- Output every 6 hours, to 15 days, on ~0.25°.
- ECMWF also runs **AIFS ENS** (50-run AI ensemble) – in the free data, not used yet (see options).

### SEAS5 – seasonal forecast system
- IFS-based coupled atmosphere–ocean model, 51 runs, started on the 1st, published on the 5th of each month.
- Says whether a month is likely **warmer/cooler, wetter/drier than normal** (normal = 1993–2016), not daily weather.

## What BOM uses
- BOM's own model family is **ACCESS** (now version APS4):
  - **ACCESS-G** – global, ~13 km, 4 times a day, to 10 days.
  - **ACCESS-GE** – global ensemble, ~33 km, to 10 days.
  - **ACCESS-C** – city models (e.g. Sydney), ~1.5 km, to ~36 h – better for local storms and sea breezes.
  - **ACCESS-S2** – seasonal (on Copernicus since May 2025).
- BOM's public 7-day forecasts are **not one model**: forecasters blend ACCESS with international models (ECMWF and
  others) and adjust by hand. That is why BOM's city numbers can differ from raw ECMWF.
- BOM partners with ECMWF and has access to ECMWF data.

## BOM data we use (since 18 Oct)
- **BOM city forecasts** – the precis XML BOM publishes for each capital (BOM FTP, `ftp://ftp.bom.gov.au/anon/gen/fwo/`):
  daily high, low, rain range, chance of rain, words; 7 days. Fetched on every refresh, every issue kept (`data\cities\bom`).
  This is BOM's **final, forecaster-adjusted** forecast for the city station – the number the market reads.
- **BOM ACCESS-S2 seasonal** – from Copernicus (centre "bom", system 2), 110 runs, same grid and units as ECMWF SEAS5.
- **BOM observations** (W-008a, since 18 Oct, history from 1 Sep 2026) – what actually happened at the city station:
  - Daily Weather Observations (monthly CSV, `bom.gov.au/climate/dwo/`): low (24 h to 9 am), high (24 h from 9 am),
    rain (24 h to 9 am), sunshine hours, max gust. This month + last month read on every refresh → no gaps if refreshes
    are weeks apart.
  - Latest observations (JSON, `bom.gov.au/fwo/`, every 30 min, last 3 days): temperature, humidity, wind, cloud.
  - Stations: Brisbane, Sydney (Observatory Hill), Melbourne (Olympic Park), Adelaide (West Terrace), Hobart (Ellerslie Road)
    – the same stations BOM's city forecasts are for.
  - Kept forever in `data\obs\daily.parquet` and `data\obs\halfhourly.parquet`.

## Other models we could add (backlog – ask first)
| Option | What it adds | Cost / effort |
|---|---|---|
| **Other seasonal centres** (W-011: UK Met Office, Météo-France, DWD, US, Japan, Canada on Copernicus) | Agreement between centres | Free, same key, small |
| **AIFS ENS** (W-009) (ECMWF AI ensemble) | A range from the AI model too | Free, same source, ~+12 GB per refresh |
| **NOAA GFS / GEFS** (W-010, US model + ensemble) | A fully independent second opinion | Free (public domain), +2–10 GB |
| **BOM ACCESS-G / ACCESS-C raw data** | BOM's own model, high-detail city model | Not free for open download as far as we know – needs checking with BOM |
