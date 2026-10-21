# L1 – Region, 6-month outlook vs normal
| | |
|---|---|
| **Code** | **L1** |
| Kind | `seasonal` – add as many as you like, each with its own region and field |
| Built-in page | Seasonal |
| Status | Built 18 Oct 2026. W-007 (BOM ACCESS-S2) built 18 Oct. W-011a (CFS, US) 21 Oct – not released |

## Question it answers
Are the coming months likely to be warmer / cooler, wetter / drier, windier / calmer, sunnier / duller than normal –
and do **ECMWF, BOM and the US model (CFS)** agree? The backdrop for monthly and quarterly hedging.

## What you see
- **Title bar:** code L1 · region picker (NSW / QLD / VIC / SA / TAS) · field picker (Temperature / Wind 10 m /
  Solar / Rain) · ⓘ (this card's "How to read it") · ▁ minimise. Edit mode adds A− / A+ (text size) and ✕ (remove).
  Region and field are remembered per panel, so a page can hold e.g. NSW temperature next to NSW wind.
- **Run pickers (W-017):** **forecast month** (default: latest) and **vs** (– none – or any earlier month on disk;
  default: last month). Remembered per panel.
- **With a vs month:** a ◆ marker on each bar = last month's forecast for the same month (each model);
  table **Change** column = change in chance above normal (e.g. `60 → 85 %`). Only months both forecasts cover.
- **Bars per month:** left = **ECMWF SEAS5** (average of 51 runs), middle = **BOM ACCESS-S2** (average of its runs,
  lighter colour), right = **CFS** US model (average of its runs, outline only). Red = above normal, blue = below for temperature; green/brown for rain; orange/purple for wind and solar.
- **Whiskers:** range 10–90 % of each model's runs.
- **Table:** Month · ECMWF average + **chance above normal** · BOM average + chance · CFS average + chance.
  Yellow = clear lean (≥ 70 % or ≤ 30 %).

## Model and data
- **ECMWF SEAS5**, 51 runs; **BOM ACCESS-S2**, ~110 runs; **NCEP CFSv2** (US, NOAA), 120 runs. All from Copernicus (C3S, dataset
  seasonal-postprocessed-single-levels), same 1° grid, nearest square per city, same key.
- ECMWF new forecast on the 5th of each month; the Copernicus multi-model set (incl. BOM, CFS) by the 10th–13th.
  CFS here is the monthly Copernicus version – NOAA's own daily CFS runs (e.g. on Tropical Tidbits) can move in between.
- Normal = each model's own 1993–2016 average for that month (so the three are fair to compare).
- Fields: 2 m temperature (°C), rain (mm/day), **10 m** wind (km/h – 100 m not available), solar (W/m²) – a field
  missing from a model is left blank.

## How to read it
- Look at the **chance**, not just the bar: +0.3 °C with 90 % chance is a stronger signal than +0.8 °C with 60 %.
- ~50 % = no signal. 70 %+ = a clear lean. **Two or three models leaning the same way = more confidence.**
- Month 1 is the current month (part already happened).

## Limits
- Monthly averages only – says nothing about single heatwaves or wind lulls.
- Seasonal skill in Australia is modest outside strong El Niño / La Niña / Indian Ocean signals.
- CFS (US) solar leaned much sunnier than ECMWF and BOM in every month and region (Oct 2026 issue, 75–95 % of runs) –
  treat its solar with care until we see more months.
- BOM's own published outlooks (bom.gov.au/climate/ahead) use ACCESS-S2 with BOM's own processing – numbers can differ a little.

## Change log
- 18 Oct 2026 – built (ECMWF only).
- 18 Oct 2026 – W-007 agreed and built: BOM ACCESS-S2 beside ECMWF.
- 20 Oct 2026 – W-017 built: forecast month + vs pickers, ◆ last month, Change column.
- 20 Oct 2026 – W-015 built: free panel, own region + field picker, ⓘ help.
- 21 Oct 2026 – W-011a agreed: CFS (US, NOAA) as a third model – bar, whiskers, ◆, table columns; also on the map.
