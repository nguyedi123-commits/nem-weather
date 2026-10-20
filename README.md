# nem-weather

Weather screen for NEM trading (Australia's east coast: QLD, NSW, VIC, SA, TAS).

- **Forecasts:** ECMWF main model (IFS), AI model (AIFS), 50-run ensemble, SEAS5 seasonal. Also BOM city forecasts,
  BOM observations and BOM's ACCESS-S2 seasonal forecast.
- **Cloud job** (`.github/workflows/refresh.yml`): twice a day it downloads the forecasts on GitHub's computer and keeps
  only the NEM east coast. It publishes small files on the release
  [`data`](../../releases/tag/data), listed in `manifest.json`.
- **Weather.exe** (`3. Code/weather`): one window. It picks up new cloud files every hour and shows pages of panels:
  Short, Medium, AI vs IFS, Seasonal and Map.
- **Docs:** `4. Docs` (one card per panel, models, backlog), plus `PLAN.md`, `CONTEXT.md` and `SKILL.md`.

Data: ECMWF open data (CC BY 4.0), Bureau of Meteorology, Copernicus Climate Change Service.
