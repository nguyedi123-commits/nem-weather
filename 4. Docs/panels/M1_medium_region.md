# M1 – Region, next 15 days with range
| | |
|---|---|
| **Code** | **M1** |
| Kind | `medium` – add as many as you like, each with its own region and field |
| Built-in page | Medium |
| Status | Built 18 Oct 2026 – not released |

## Question it answers
Over the next two weeks, what is the likely weather, and **how sure** is the forecast? Where is there a risk of a
heat event, a wind lull, a dull or wet spell?

## What you see
- **Title bar:** code M1 · region picker (NSW / QLD / VIC / SA / TAS) · ⓘ (this card's "How to read it") · ▁ minimise. Edit mode adds A− / A+ (text size) and ✕ (remove).
  **What to show (Temperature / Rain / Solar / Wind) is one picker in the top bar** – all region charts on the page
  follow it; each page remembers its own choice (user, 23 Oct). Region is remembered per panel.
- **Run pickers (W-017)**, after the title: **run** (default: latest) and **vs** (– none – or any earlier run on
  disk; default: the same time yesterday, else the run before). Remembered per panel.
  Runs here are **ensemble** runs (00z, once a day).
- **With a vs run:** temperature / wind – the vs run's middle line **dashed** and its 10–90 % range as thin dashed
  edges; rain / solar – a hollow marker for the vs run's middle. Table **Change** column: high / low middle and
  rain chance vs that run (e.g. `+1.5 / +0.8 · rain 20→70%`). Big changes in yellow.
- When an older run is picked, the IFS and AIFS lines show the runs of that same time if they are on disk.
- **Temperature / Wind 100 m chart:**
  - Grey band = range 10–90 % of the 50 ensemble runs (8 in 10 runs fall inside).
  - Thick grey line = the middle run (median).
  - Blue line = IFS main model (single run). Purple line = AIFS AI model.
- **Rain / Solar chart:** one bar per day = middle run's day total; whiskers = 10–90 % range;
  blue dot = IFS, purple diamond = AIFS.
- **Daily table:** High and Low as "middle (low–high range)"; Rain = middle run mm + % chance of at least 1 mm;
  Wind = day average; Sun = day total kWh/m²; **BOM** = BOM's high / low, rain range and chance (BOM forecasts 7 days).
- Temperature chart: BOM's daily high ▲ and low ▼ for its 7 days.

## Model and data
- **IFS ensemble** (ECMWF, 50 runs, 00z run) – 6-hourly to day 7, then 4 am and 4 pm NEM time to day 15.
  Fields: temperature + true max/min, 100 m wind, rain, solar.
- **IFS** single run (latest 00z/12z) – 3-hourly to day 6, 6-hourly after.
- **AIFS Single** (ECMWF AI model, latest 00z/12z) – 6-hourly.
- **BOM city forecast** (latest, 7 days).
- See [MODELS.md](../MODELS.md).

## How to read it
- **Narrow band** = models agree, high confidence. **Wide band** = several outcomes possible – plan for both ends.
- If IFS or AIFS sits at the edge of the band, it is an outlier run – trust the middle more.
- Rain chance ≥ 70 % = likely wet day; ≤ 20 % = likely dry.
- Confidence usually drops after day 5–7; days 10–15 are about the trend (warmer / cooler spell), not the exact number.

## Limits
- Days 8–15 have only 2 values a day (4 am / 4 pm), so peaks between can be missed in the **chart**. The table and I1
  use the true daily high / low: since 21 Oct (W-022) the ensemble's max / min covers **all 24 hours** of every day
  (extra max/min-only steps, feed `ensx`). Runs before that covered only part of the day (lows too warm, late or
  early peaks missed).
- Ensemble "control" run (51st) not downloaded.
- Raw model, no BOM correction yet.

## Change log
- 18 Oct 2026 – built.
- 18 Oct 2026 – W-006 agreed and built: BOM high / low markers + BOM column.
- 20 Oct 2026 – W-022 built: full-day max / min for the ensemble (extra max/min-only steps).
- 20 Oct 2026 – W-017 built: run + vs pickers, dashed older run, Change column.
- 20 Oct 2026 – W-015 built: free panel, own region + field picker, ⓘ help.
- 23 Oct 2026 – IFS line always from the newest 15-day run (00z / 12z), not the midday 18z run (to 90 h only).
- 23 Oct 2026 – field picker moved to the top bar: one choice for every region chart on the page (W-025).
