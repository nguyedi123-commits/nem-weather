# W1 – Week ahead: every state, every day, at a glance
| | |
|---|---|
| **Code** | **W1** |
| Kind | `week` – one panel, no pickers |
| Built-in page | **Overview** (first tab, opens on start) – across the top, I1 Insights and A1 About below |
| Status | W-026 agreed 23 Oct 2026 – building |

## Question it answers
Which days and which states matter over the next two weeks – heat, cold, wind lulls, dull days, rain – and which way
that usually pushes power prices? One look, before opening any chart.

## What you see
- **Rows:** NSW · Sydney, QLD · Brisbane, VIC · Melbourne, SA · Adelaide. **Columns:** the next full days, as far as the
  ensemble reaches (up to 14; ~13 just before a new ensemble run). Today is left out (the Short page has it).
- **Each cell:**
  - **Big number** = the day's high (°C); small number = the night's low.
  - **Colour** = the high against that city's heat limit (card I1): dark red = very hot (4 °C or more above the limit),
    red = hot, orange = warm (within 4 °C below), white = mild; **blue** = cold night (low at or below the cold limit).
  - **Small tags** when a rule fires: **Lull** (wind lull), **Windy** (strong wind), **Dull** (dull day), **Wet** / **Heavy**
    (rain), **Rain** (rain likely, ≥ 70 % chance), **Risk** (heat risk: 1 in 10 ensemble runs reach the heat
    limit).
  - **Price arrow** in the corner: red ▲ / green ▼ = the direction the tagged weather usually pushes prices (same rules as
    I1); ▲▼ = both kinds on the same day.
- **Hover** a cell: high, low, wind, sun, rain + chance, and the reasons for the arrow.
- **Click** a cell: opens that day's page – Short for days 1–3, Medium after – with that state's chart.
- **Column heads:** the day; days from the ensemble are marked "Ens" and drawn a little paler (less certain).
- Subtitle: the runs used, e.g. "IFS Fri 23 Oct 04:00 · Ensemble Thu 22 Oct 10:00".

## Model and data
- **Days 1–3: IFS main model** (newest run, sharpest detail) – the same daily numbers as the S1 table.
- **Days 4–14: IFS ensemble middle** (50 runs) – the same daily numbers as the M1 table; the heat-risk tag uses the
  top of its range.
- Temperature and rain: the city square (nearest ≥ 90 % land square). **Wind and sun: average of the state's farm areas**
  (W-027, list in MODELS.md); hover shows each area. Wind = day-average at 100 m. Sun = kWh/m² for the day.
- Rules and limits: exactly the I1 rules (heat / cold / lull / strong wind / dull / wet / likely rain), card I1.

## How to read it
- Scan for red and ▲: those are the days and states to look at first; click through for the detail.
- A pale day 10 that turns red on later runs = a signal firming up (W-028 alerts will flag that later).
- Wind and sun are at the farm areas, but still weather – not farm output (no curtailment, outages, turbine limits).

## Limits
- Days 4–14 are the ensemble **middle**: a real heatwave on day 10 can look milder here than it will turn out
  (the Risk tag catches some of that).
- Rules, not a forecaster; arrows are a direction, not a price forecast.
- TAS not shown (as I1).

## Change log
- 23 Oct 2026 – W-026 agreed: new Overview page, up to 14 days (IFS days 1–3, ensemble after), high + low + colour + tags + arrow.
- 23 Oct 2026 – W-027: wind and sun = farm-area average; hover lists each area.
