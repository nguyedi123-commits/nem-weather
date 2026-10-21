# A1 – About this page
| | |
|---|---|
| **Code** | **A1** |
| Kind | `about` – can go on any page |
| Built-in pages | Short, Medium, AI vs IFS, Seasonal (bottom-right) |
| Status | Built 18 Oct 2026 – not released |

## Question it answers
What am I looking at, and how fresh is it?

## What you see
- Short notes on the page's panels (what the colours mean); full notes behind each panel's ⓘ.
- **Forecast runs on screen** (NEM time): IFS, AIFS, ensemble run time + hours old (red if > 30 h); seasonal month.
- **Download progress** while a refresh runs (W-016): which model, step x of y, %, GB so far.
- **Cloud (W-019):** when the cloud last made new data, when Weather last checked, next check (every 15 minutes).
- Reminder: new data only when a refresh is asked for. Data credit: ECMWF, CC BY 4.0.

## Model and data
Reads `data\catalog.json` (finished runs) via `/api/status`, checked every 60 s.

## How to read it
If a run is red (> 30 h old), the screen is out of date – ask for a refresh.

## Limits
Notes are a summary – the full explanation is in the tab's card (S1, M1, C1, L1).

## Change log
- 18 Oct 2026 – built.
- 20 Oct 2026 – W-019 agreed: cloud status lines.
- 20 Oct 2026 – W-015 / W-016 built: free panel, download progress.
- 21 Oct 2026 – W-024: cloud checked every 15 minutes (was hourly) so the 7 am data is in by ~7:15 am Sydney.
