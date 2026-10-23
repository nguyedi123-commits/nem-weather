# F1 – Forecast check: how close were the forecasts to what BOM measured?
| | |
|---|---|
| **Code** | **F1** |
| Kind | `check` – one panel per state; pickers: region · measure (Highs / Lows / Rain / Sunshine) · period (14 / 30 / 90 days) |
| Built-in page | **Check** (6th tab): NSW, QLD (top) · SA, VIC (bottom) |
| Status | W-014 built 23 Oct 2026 – not released. **Few days to check yet** (forecasts kept since ~18 Oct) |

## Question it answers
Which forecast can I trust for this state, and how far ahead – and does a model run warm or cold here?

## What you see
- **Table:** rows **IFS · AIFS · Ensemble (middle) · BOM**, columns **day 1, 2, 3, 5, 7 ahead**.
  - **Highs / Lows:** average miss in °C (smaller = better) and the lean: e.g. `1.2° · 0.8 cool` = off by 1.2 °C on
    average, and 0.8 °C too cool on average. Green = best in that column.
  - **Rain:** % of days it got right whether it would rain (≥ 1 mm) or stay dry.
  - **Sunshine:** how well sunny and dull days matched, 0–100 % (see Model and data).
  - Hover a cell: number of days checked. "–" = no days yet.
- **Chart:** the last 14 days – what happened (black) against each forecast made the day before (day 1).
  Highs / Lows: °C; Rain: mm; Sunshine: sun hours (black) against forecast sun (kWh/m², right-hand scale).
- Subtitle: days checked and the period.

## Model and data
- **Measured:** BOM Daily Weather Observations at the city station (W-008a): high = 24 h from 9 am, low = 24 h to 9 am,
  rain = 24 h to 9 am (so the rain for a day is the figure recorded the **next** morning), sunshine hours.
- **Forecasts:** every run kept on this PC – IFS, AIFS, ensemble middle (50 runs), and BOM's own city forecast.
  **Day N ahead** = the target day is N days after the day the run started (NEM time); for several runs that day, the
  latest. BOM: the latest issue N days before.
- Model values at the **city** square (temperature, rain and sun – not the farm areas, so they match the station).
- AIFS has no true max / min: its highs / lows come from 6-hourly values (usually a bit too mild – shows as a lean).
- Sunshine score = how closely the forecast's day-to-day sun follows the measured sun hours (a correlation shown as
  0–100 %; 70 %+ = good). Needs at least 5 days.

## How to read it
- Pick the model with the smallest miss for the day you trade; if a model leans (e.g. 1.5 cool), mentally add it back.
- A big lean in one state only (e.g. Brisbane highs) is a local effect – that is what the BOM correction (W-008b) will fix.
- **Few days = shaky numbers.** Look at the "days checked" before trusting a difference.

## Limits
- Forecasts on disk only from ~18 Oct 2026; days 5 and 7 fill in a week later. Wait for ~30 days before drawing
  conclusions.
- City station vs a 25 km model square: some miss is just the square, not the forecast.
- **Sunshine is only measured at Sydney (and Brisbane on most days)** – Melbourne and Adelaide stations don't record
  it, so VIC / SA say "not measured here".
- TAS not shown.

## Change log
- 23 Oct 2026 – W-014 agreed: highs, lows, rain yes/no, sunshine; IFS / AIFS / ensemble / BOM; days 1, 2, 3, 5, 7; new Check page.
