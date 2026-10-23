# S1 – Region, next 3 days
| | |
|---|---|
| **Code** | **S1** |
| Kind | `short` – add as many as you like ("+ Add panel"), each with its own region and field |
| Built-in page | Short (NSW, QLD, VIC · SA, TAS · A1) |
| Status | Built 18 Oct 2026 – not released. W-005 / W-006 built 18 Oct |

## Question it answers
What will the weather do in each region over the next 3 days, hour by hour – and how sure is it? The days that
matter most for demand, wind and solar bids.

## What you see
- **Title bar:** code S1 · region picker (NSW / QLD / VIC / SA / TAS) · ⓘ (this card's "How to read it") · ▁ minimise. Edit mode adds A− / A+ (text size) and ✕ (remove).
  **What to show (Temperature / Rain / Solar / Wind) is one picker in the top bar** – all region charts on the page
  follow it; each page remembers its own choice (user, 23 Oct). Region is remembered per panel.
- **Run pickers (W-017)**, after the title: **run** (default: latest) and **vs** (– none – or any earlier run on
  disk; default: the same time yesterday, else the run before). Remembered per panel.
- **With a vs run:** the vs run's IFS line is drawn **dashed** in the same colour (temperature, wind, solar; rain as
  hollow bars) over the same 3 days; the table gets a **Change** column: high / low / rain vs that run
  (e.g. `+2.1 / −0.4 / +6 mm`). Big changes (±2 °C, ±5 mm) in yellow.
- **Chart** (field from the title bar):
  - Temperature °C / Wind 100 m km/h:
    - blue line = IFS main model, every 3 hours (the best guess);
    - grey band = range 10–90 % of the 50 ensemble runs (8 in 10 runs inside), every 6 hours;
    - purple line = AIFS AI model, every 6 hours;
    - temperature only: **BOM's** forecast high ▲ and low ▼ for each day.
  - Solar W/m² – IFS, average over each 3 hours (drawn at the middle of the period) + ensemble 10–90 % band
    (6-hour averages); dashed line = IFS cloud cover %.
  - Rain – IFS mm in each 3 hours (bars).
- **Daily table** (first 4 days):
  - High / Low °C (IFS), Rain (IFS day total mm) with the **ensemble chance of ≥ 1 mm**, Wind (day average km/h),
    Sun (day total kWh/m²);
  - **BOM** column: BOM's high / low, rain range and chance of rain (BOM's latest city forecast).
  - Grey italic rows = part days (the run starts or ends during that day).

## Model and data
- ECMWF **IFS** single run (latest on disk), 3-hourly. One 25 km grid square per city: nearest square that is
  ≥ 90 % land (Adelaide set by hand). High / Low use ECMWF's true max/min temperature in each 3 h.
- ECMWF **IFS ensemble** (50 runs, latest 00z run), 6-hourly – range band and rain chance.
- ECMWF **AIFS Single** (latest), 6-hourly.
- **BOM city forecast** (precis XML from BOM's FTP, the forecast BOM publishes for the city) – fetched on refresh.
- Times NEM time (AEST). See [MODELS.md](../MODELS.md).

## How to read it
- Dashed line far from the solid line = the forecast moved since that run; the Change column says how much.
- Blue line inside a **narrow band** = confident. Blue line near the band's edge, or a wide band = the outcome could
  differ a lot – plan for both ends.
- IFS and AIFS together: agree = more confidence.
- **ECMWF vs BOM:** BOM's numbers are for the station and are adjusted by forecasters; ECMWF is a 25 km square
  average. A steady gap (e.g. ECMWF 2 °C cooler every day) is the model's usual bias; a gap on one day only means the
  two disagree about the weather.
- Solar dips with cloud: dashed cloud line near 100 % at midday = weak solar.
- 1 kWh/m² of daily sun ≈ a dull day; 7–8 kWh/m² ≈ a clear spring/summer day.

## Limits
- Ensemble band is 6-hourly (the 3-hourly ensemble was not downloaded to save ~4 GB per refresh).
- Ensemble may be one run older than IFS (we take the ensemble once a day, 00z).
- Raw model, no BOM correction yet (W-008).
- BOM forecast uses local time days (daylight saving) – matched to the same calendar date.

## Change log
- 18 Oct 2026 – built (IFS only).
- 18 Oct 2026 – W-005 / W-006 agreed and built: ensemble band, AIFS line, rain chance, BOM forecast.
- 20 Oct 2026 – W-017 built: run + vs pickers, dashed older run, Change column.
- 20 Oct 2026 – W-015 built: free panel (add / move / resize / remove), own region + field picker, ⓘ help.
- 23 Oct 2026 – field picker moved to the top bar: one choice for every region chart on the page (W-025).
