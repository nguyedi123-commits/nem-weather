This is my agent workspace for **Weather** – a stand-alone weather screen for the NEM trading PC, built from
ECMWF forecasts (https://data.ecmwf.int/forecasts/, free, CC BY 4.0) + Copernicus seasonal forecasts (SEAS5).
Python + a local web page (same build style as NEM Trader: pywebview, ECharts).

- Purpose: Australia east-coast weather (QLD, NSW, VIC, SA, TAS) – short (0–3 days), medium (to 15 days),
  seasonal (to 6 months), AI model vs main model – for trading (demand, wind, solar).
- Look and layout copied from **NEM Trader**: `Documents\AI\21) NEM Screens\6. NEM Trader` (dev http://127.0.0.1:8890).
  Weather is its own program; code is copied in, not shared.
- Dev copy runs at **http://127.0.0.1:8892**. Weather.exe will run on **one screen, one window** (no multi-monitor).
- Works like NEM Trader: pages of panels, Edit mode (Ctrl+E) to add / move / resize / remove panels and pages.

Start every session by reading CONTEXT.md and SKILL.md, then PLAN.md, then `4. Docs\README.md` (and the card of any panel we touch).

# How we work
- PLAN.md = what we build, the steps, test results, open items. CONTEXT.md = where things stand now. SKILL.md = how.
- One step at a time: build → test locally → show results → I confirm → next step.
- **Every panel has a card** `4. Docs\panels\<code>_<name>.md`: what it means, which forecast model, how to read it
  (headings: Code · Question it answers · What you see · Model and data · How to read it · Limits · Change log).
  New panel or change → write/update the card **first**, then code; index in `4. Docs\README.md`.
  Models explained in `4. Docs\MODELS.md` – update it when a model or feed changes.
- **No .exe / zip until I say "release".**
- Never keep the global ECMWF files – only the east coast (disk must stay small).
- The trading PC is switched off at random: downloads must resume where they stopped.
- **No automatic downloads (for now).** Only refresh data when I ask (~18 GB per full refresh – fine on home internet,
  not at the office). The app only shows what is already in `data\`.

# About me
I prefer clean, jargon-free output.

# Rules
- Make it simple for both of us to pick things/projects up easily.
- **Outstanding actions must be asked**: never assume something worked - list every open item and ask me to confirm before calling a job done
- Always ask clarifying questions before starting a complex task
- Any missing table/view or context: ask me, do not assume
- Show your plan and steps before executing
- Keep reports and summaries concise
- Bullet points over paragraphs
- Save all output files to `2. Output`
- Test locally first
- Ask me questions before a complex task until you are 95% confident

# Project structure
- `1. Input` – reference material
- `2. Output` – the zips to install / update; `2. Output\screenshots` – test pictures
- `4. Docs` – panel cards (`panels\`), index (`README.md`), models (`MODELS.md`)
- `3. Code\weather` – the program: `backend\` (downloaders, server), `web\` (page), `run_download.py` (command line)
- `data` – downloaded east-coast data (cities, grid, obs, catalog, progress); not shipped
- `settings` – saved pages (`layouts\`) and screen settings (theme, last page); built-in pages in `3. Code\weather\web\layouts\`
- `.venv` – Python 3.14 environment (recreate if the folder moves – see SKILL.md)
- `PLAN.md`, `CONTEXT.md`, `SKILL.md` – plan, current state, how-to
