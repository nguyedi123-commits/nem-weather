# C1 – Region, AI model vs main model
| | |
|---|---|
| **Code** | **C1** |
| Kind | `compare` – add as many as you like, each with its own region and field |
| Built-in page | AI vs IFS |
| Status | Built 18 Oct 2026 – not released |

## Question it answers
Do ECMWF's two best-guess models – the physics model (IFS) and the AI model (AIFS) – agree? Where they split, the
weather is harder to call.

## What you see
- **Title bar:** code C1 · region picker (NSW / QLD / VIC / SA / TAS) · field picker (Temperature / Wind 100 m /
  Solar / Rain) · ⓘ (this card's "How to read it") · ▁ minimise. Edit mode adds A− / A+ (text size) and ✕ (remove).
  Region and field are remembered per panel, so a page can hold e.g. NSW temperature next to NSW wind.
- **Temperature / Wind 100 m:** blue line = IFS, purple line = AIFS, to 15 days.
- **Rain / Solar:** daily totals, blue bar = IFS, purple bar = AIFS.
- **Table:** each day "IFS / AIFS" for High, Low, Rain, Wind, Sun. **Yellow** = big difference
  (≥ 3 °C, ≥ 5 mm rain, ≥ 10 km/h wind, ≥ 1.5 kWh/m² sun).

## Model and data
- **IFS** single run (latest 00z/12z), 3-hourly to day 6, then 6-hourly.
- **AIFS Single** (latest 00z/12z), 6-hourly. See [MODELS.md](../MODELS.md).

## How to read it
- Agreement = more confidence. A yellow cell = check M1: is the ensemble range wide on that day too?
- AIFS is usually smoother: smaller peaks, less extreme rain. A big IFS rain day that AIFS doesn't show is a "maybe".

## Limits
- AIFS has no true hourly max/min: its High/Low are the warmest/coolest 6-hourly values → can look milder.
- Both are single runs: neither shows uncertainty by itself.

## Change log
- 18 Oct 2026 – built.
- 20 Oct 2026 – W-015 built: free panel, own region + field picker, ⓘ help.
- 23 Oct 2026 – IFS always the newest 15-day run (00z / 12z), not the midday 18z run (to 90 h only).
