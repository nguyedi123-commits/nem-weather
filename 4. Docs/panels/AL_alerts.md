# AL – Alerts: a new run changed something big
| | |
|---|---|
| **Code** | **AL** (top bar, not a panel) |
| Kind | **Alerts** button in the top bar, on every page |
| Status | W-028 agreed 23 Oct 2026 – building |

## Question it answers
Did the newest forecast change anything that matters for the next 7 days – without me checking every page after every
cloud job?

## What you see
- **Alerts** button in the top bar with a **red dot and number** = alerts you haven't seen yet. No dot = nothing new.
- **Click** = the alert list, newest run first. Each run has a heading, e.g. "IFS Fri 23 Oct 15:00 vs Fri 23 Oct 04:00 –
  3 alerts". Each alert:
  - **New warning**: `NSW Sat 24 – new: Wind lull (11 km/h at the farm areas) · price ▲`
  - **Warning gone**: `VIC Sun 25 – no longer: Hot (high 36 → 33 °C)`
  - **Big change**: `SA Mon 26 high 29 → 33 °C (+4)`
- **Mark all seen** clears the dot. The list keeps the last 7 days.

## Model and data
- **Which runs:** every new **IFS** run (overnight, midday, day run) for **days 1–3**, and every new **ensemble** run (middle
  of 50) for **days 4–7** – the same split as the week grid (W1). Each run is compared with the run of the same model just
  before it.
- **Days 1–7 only** (tomorrow to 7 days ahead; later days move a lot from run to run). Today is left out.
- **Warnings** = the I1 rules: Hot, Very hot, Cold night, Wind lull, Strong wind, Dull day, Heavy rain. (Wet, Rain likely and
  Heat risk are not alerted – they come and go too easily.)
- **Big changes** = the "Changed since" limits: high / low ±2 °C, rain ±5 mm, rain chance ±30 points (ensemble),
  wind ±10 km/h, sun ±1.5 kWh/m².
- Wind and sun = the state's farm areas (W-027); temperature and rain = the city. NSW, QLD, VIC, SA.
- Saved in `data\alerts.json` on this PC (works the same on the trading PC – each PC has its own "seen").

## How to read it
- A **new warning in days 1–3** is the one to act on; days 4–7 are early signs.
- Several runs in a row pointing the same way = the signal is firming up.
- Click through to the Overview grid or the page for the detail.

## Limits
- Only what the rules see: a change just under a limit (e.g. +1.9 °C) is not alerted.
- The first time the program sees a run there is nothing to compare with – alerts start from the next run.
- When one run has farm-area wind / sun and the other still the city (the 23 Oct evening switch), wind and sun are
  not compared for that pair (the heading says so).
- Rules, not a forecaster; price arrows are a direction, not a forecast.

## Change log
- 23 Oct 2026 – W-028 agreed: new warnings + big changes, days 1–7, IFS (days 1–3) + ensemble (days 4–7), red dot + list.
