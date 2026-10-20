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
- **Title bar:** code M1 · region picker (NSW / QLD / VIC / SA / TAS) · field picker (Temperature / Wind 100 m /
  Solar / Rain) · ⓘ (this card's "How to read it") · ▁ minimise. Edit mode adds A− / A+ (text size) and ✕ (remove).
  Region and field are remembered per panel, so a page can hold e.g. NSW temperature next to NSW wind.
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
- Days 8–15 have only 2 values a day (4 am / 4 pm), so peaks between can be missed in the chart; the table still uses
  the true max/min. Days 1–7 highs use 3-hour max windows every 6 hours – can read slightly low.
- Ensemble "control" run (51st) not downloaded.
- Raw model, no BOM correction yet.

## Change log
- 18 Oct 2026 – built.
- 18 Oct 2026 – W-006 agreed and built: BOM high / low markers + BOM column.
- 20 Oct 2026 – W-017 built: run + vs pickers, dashed older run, Change column.
- 20 Oct 2026 – W-015 built: free panel, own region + field picker, ⓘ help.
