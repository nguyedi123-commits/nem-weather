# I1 – Insights: what the latest run says and what changed
| | |
|---|---|
| **Code** | **I1** |
| Kind | `insights` – one panel, **page picker** (Short / Medium / AI vs IFS / Seasonal) |
| Built-in pages | Short, Medium, AI vs IFS, Seasonal – bottom right (where TAS was) |
| Status | Built 20 Oct 2026 (W-021) |

## Question it answers
In plain words: what stands out in the newest forecast for **NSW, QLD, VIC and SA**, and what changed since yesterday? It's
a quick read so nobody has to scan every chart.

## What you see
- **Title bar:** code I1 · **page** picker · ⓘ · ▁. The subtitle shows which runs are compared, e.g. "20 Oct 10:00 vs 19 Oct 10:00".
- **Headlines:** up to 5 bullets with the biggest things, most important first. Red = heat / storm-type risk, blue = cold,
  amber = wind or solar, grey = for information.
- **By region:** NSW, QLD, VIC, SA, each a few bullets (e.g. `Thu 34 °C – hottest day; dull day Fri (2.1 kWh/m²)`).
- **Changed since <earlier run>:** the notable changes, e.g. `NSW Thu high 31 → 34 °C (+3)`, `SA Sat rain chance 20 → 70 %`.
- "Nothing stands out" when no rule fires.

## Model and data
Each page reads its own data and the same run as the page's default (latest, vs same time yesterday):

| Page | Looks at | "Changed since" |
|---|---|---|
| Short | IFS next 3 days (+ ensemble rain chance, BOM high/low) | IFS vs the IFS run 24 h before |
| Medium | Ensemble next 15 days: middle + 10–90 % range | ensemble vs yesterday's ensemble (middle, rain chance) |
| AI vs IFS | days where IFS and AIFS disagree | each model vs its own run 24 h before |
| Seasonal | months with a clear lean (ECMWF; whether BOM and CFS (US) agree) | chance above normal vs last month's forecast |

**Rules (starting limits, can be changed):**
- **Heat** (day high): Sydney / Brisbane ≥ 32 °C, Melbourne ≥ 35 °C, Adelaide ≥ 36 °C. **Very hot** = 4 °C above.
- **Cold** (overnight low): Sydney / Brisbane ≤ 8 °C, Melbourne / Adelaide ≤ 5 °C.
- **Wind lull** = day-average 100 m wind ≤ 12 km/h. **Strong wind** ≥ 40 km/h.
- **Dull day** = sun ≤ 3 kWh/m². **Wet day** = rain ≥ 10 mm (heavy ≥ 25 mm). **Likely rain** = ensemble chance ≥ 70 %.
- Medium only: **uncertain** when the 10–90 % range of the high is 8 °C or wider; **heat risk** when the top of the range
  (90 %) reaches the heat limit even though the middle doesn't.
- AI vs IFS: **disagree** when highs differ by 3 °C or more, rain by 5 mm, wind by 10 km/h, or sun by 1.5 kWh/m².
- Seasonal: **clear lean** = chance above normal ≥ 70 % or ≤ 30 %. **Changed** = chance moved by 20 points or more.
- Changes use the same limits as D1 (±2 °C, ±5 mm, ±30 points rain chance, ±10 km/h, ±1.5 kWh/m²).

## How to read it
- Headlines first; open the page's charts for the detail.
- "Changed since" in the next 1–3 days is the forecast firming up and matters most. Changes at day 8–15 are early signs.
- The wind rules use the **city** grid square. They hint at wind-farm weather but are not wind-farm output.

## Limits
- Rules, not a forecaster: the wording is fixed and simple.
- TAS is left out on purpose (small position). Ask to add it back.
- With only one run on disk there's no "Changed since" (it says so).

## Change log
- 20 Oct 2026 – agreed and built (W-021). Built-in pages now: NSW, QLD, About · SA, VIC, I1 (no TAS).
- 21 Oct 2026 – W-011a: seasonal lines also say whether CFS (US) agrees (after BOM).
