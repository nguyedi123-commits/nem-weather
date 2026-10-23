# Weather – docs

**Rule (18 Oct 2026):** every panel has a card in `panels\<code>.md` that says what it means, which forecast
model it uses and how to read it. No new or changed panel without its card being written / updated first.

## Panel cards
| Code | Panel | Tab | Card |
|---|---|---|---|
| W1 | Week ahead: states × 15 days, colour + tags + price arrow, click through | Overview | [W1](panels/W1_week_ahead.md) |
| S1 | Next 3 days – one region (picker); field from the top-bar picker | Short | [S1](panels/S1_short_region.md) |
| M1 | Next 15 days with range – region picker; field from the top bar | Medium | [M1](panels/M1_medium_region.md) |
| C1 | AI model vs main model – region picker; field from the top bar | – (Edit mode) | [C1](panels/C1_compare_region.md) |
| L1 | 6-month outlook vs normal, ECMWF + BOM + CFS – region picker; field from the top bar | Seasonal | [L1](panels/L1_seasonal_region.md) |
| G1 | East-coast map with its own model / field / time controls | Map | [G1](panels/G1_map.md) |
| ~~G2~~ | ~~Map controls~~ – retired 20 Oct (inside G1 now) | – | [G2](panels/G2_map_controls.md) |
| A1 | About: runs on screen + download progress | all built-in pages | [A1](panels/A1_about.md) |
| D1 | What changed between two runs (all regions, notable changes only) | – (add it) | [D1](panels/D1_what_changed.md) |
| I1 | Insights: what the latest run says + what changed (NSW, QLD, VIC, SA), page picker, price tags | Overview, Short, Medium, Seasonal | [I1](panels/I1_insights.md) |

Since 20 Oct (W-015) every panel can be added to any page ("+ Add panel" in Edit mode), moved, resized, minimised
and removed; pages can be added, renamed, copied, deleted and reset. Built-in page = the default layout of a page.
The ⓘ in each title bar shows the card's "How to read it" (`web\help.json`, built from the cards by
`tools\build_help.py` – rebuild after changing a card).

Group letters: S Short · M Medium · C Compare · L Long (seasonal) · G Map · A About · D Difference (what changed) · I Insights. Codes are never reused.

## Header (not panels)
- Tabs (pages) · Edit tools (Edit mode) · status: download progress (W-016) + runs on screen · **Refresh** (W-018):
  Full / Without ensemble / BOM only – the program downloads in the background · Theme · Edit.

## Other pages
- [BACKLOG.md](BACKLOG.md) – every request by number (W-001 …), status; ideas kept for later.
- [MODELS.md](MODELS.md) – the forecast models we use (IFS, ensemble, AIFS, SEAS5), what BOM uses, other options.
- Card headings (copy for a new card): Code · Question it answers · What you see · Model and data · How to read it ·
  Limits · Change log.
