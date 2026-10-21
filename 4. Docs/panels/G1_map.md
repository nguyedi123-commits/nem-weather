# G1 – East-coast map
| | |
|---|---|
| **Code** | **G1** |
| Kind | `map` – can go on any page; its controls are inside the panel |
| Built-in page | Map |
| Status | Built 18 Oct 2026 – not released |

## Question it answers
Where is the weather happening – e.g. is the cloud band over the solar farms, where is the wind, how far does the
heat reach – at a chosen time?

## What you see
- **Title bar:** code G1 · model picker (IFS / AIFS (AI) / Ensemble middle / Seasonal / Seasonal CFS (US)) · field picker ·
  ⓘ · ▁. **Bottom strip:** time (NEM) with ◀ / ▶ and a slider; opens at the next forecast time from now.
  **⏵ Play / ⏸ Pause (W-023):** steps through the times by itself and starts again from the first time at the end;
  speed Slow / Normal / Fast (about 1.5 / 0.8 / 0.4 s per step). Moving the slider or ◀ / ▶ pauses it.
  Model, field are remembered per panel.
- **Run pickers (W-017):** **run** (default: latest; maps are kept 30 days) and **vs** (– none – or an earlier run).
- **With a vs run = change map:** colours show **chosen run minus vs run** at the same time
  (temperature: red = warmer now, blue = cooler; rain: green = wetter now, brown = drier; wind / solar likewise).
  Only times both runs cover; seasonal: same month.
- Colour map of the east coast (lat −9 to −44, lon 129 to 155): one square per 0.25° (~25 km); seasonal 1°.
- Black line = coastline (from ECMWF's land/sea mask). Dots = the 5 cities.
- Colour scale on the right with min / max and unit.

## Model and data
Chosen in the title bar: **IFS** single run · **AIFS** · **Ensemble middle** (median of 50 runs) · **Seasonal** (SEAS5 difference
from normal, average of 51 runs) · **Seasonal CFS (US)** (NOAA CFSv2 difference from normal, average of its runs). Fields: temperature, wind 100 m (seasonal: 10 m), solar, rain.

## How to read it
- Temperature: blue cool → red hot. Wind: white calm → purple strong. Solar: dark → yellow bright. Rain: white dry → dark blue heavy.
- Rain is **mm per hour** averaged over the step before the time shown (so 3 h / 6 h / 12 h steps compare);
  solar is the average over that step.
- Seasonal: blue/brown = below normal, red/green = above normal; white = normal.
- Colour scale fits the data on screen (except solar 0–1100 W/m² and rain from 0) – compare colours within one map, not between maps.

## Limits
- The ensemble map shows the **middle run only** (no range on the map).
- Map data is kept 30 days.

## Change log
- 18 Oct 2026 – built.
- 20 Oct 2026 – W-023 built: Play / Pause button with speed.
- 20 Oct 2026 – W-017 built: run + vs pickers, change map.
- 20 Oct 2026 – W-015 built: map controls moved into the panel (G2 retired).
- 21 Oct 2026 – W-011a: Seasonal CFS (US) added to the model picker.
