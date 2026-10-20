# D1 – What changed between two runs
| | |
|---|---|
| **Code** | **D1** |
| Kind | `changes` – can go on any page (not on a built-in page by default) |
| Status | Built 20 Oct 2026 (W-017) – in Weather.exe first release |

## Question it answers
What is different in the newest forecast compared with an earlier one – e.g. "Thursday in Sydney is now 3 °C hotter
and rain chance went from 20 % to 70 %"? The quick read after a refresh.

## What you see
- **Title bar:** code D1 · model picker (IFS / AIFS (AI) / Ensemble middle) · **run** picker (default: latest) ·
  **vs** picker (any earlier run on disk; default: the same time yesterday, else the run before) · ⓘ · ▁.
- **Table, all 5 regions (NSW, QLD, VIC, SA, TAS), only the notable changes**, sorted by day:
  Region · Day · what changed, as "old → new (change)", e.g. `High 25 → 28 (+3 °C)`, `Rain chance 20% → 70%`.
- Notable = high or low ±2 °C or more · rain ±5 mm or more · rain chance ±30 points or more (ensemble only) ·
  wind ±10 km/h or more · sun ±1.5 kWh/m² or more. Bigger changes in bold.
- "No big changes" when nothing passes the limits.

## Model and data
- Daily values (high, low, rain, wind, sun) of the two chosen runs, same city squares as S1 / M1, matched by day
  (NEM time). Only days both runs fully cover.
- City data of every run is kept forever, so any past run can be picked.

## How to read it
- Changes in the next 1–3 days matter most – the forecast is firming up. Big changes at day 8–15 are normal
  (the model is still guessing) – treat them as "watch this".
- A change in the **ensemble middle** is more meaningful than a change in a single run (IFS or AIFS), which can jump
  around from run to run.
- Compare like with like: today 10:00 vs yesterday 10:00 (the default) avoids small day/night differences between runs.

## Limits
- Only runs that were downloaded can be picked (refresh fetches the newest run only).
- Wind and sun changes use day averages / totals – a change in timing within the day is not shown.

## Change log
- 20 Oct 2026 – agreed and built (W-017).
