"""Settings for the ECMWF downloader: places, area, feeds, folders."""
import os
from pathlib import Path
import sys


def _writable(folder):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        t = folder / ".write-test"
        t.write_text("ok")
        t.unlink()
        return True
    except OSError:
        return False


# Data folder: next to the exe when frozen, project root when run from source.
# If the exe sits somewhere Windows won't let it write (e.g. Program Files): %LOCALAPPDATA%\Weather instead.
if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).resolve().parent
    if not _writable(BASE / "data"):
        BASE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Weather"
else:
    BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data"
SETTINGS = BASE / "settings"   # saved pages (layouts) and screen settings

# Copernicus key: a .cdsapirc next to the program (or in settings\) is used before the one in the user's folder
for _rc in (BASE / ".cdsapirc", SETTINGS / ".cdsapirc"):
    if _rc.exists():
        os.environ.setdefault("CDSAPI_RC", str(_rc))
        break

CITIES = [  # (region, city, lat, lon)
    ("QLD", "Brisbane", -27.47, 153.03),
    ("NSW", "Sydney", -33.87, 151.21),
    ("VIC", "Melbourne", -37.81, 144.96),
    ("SA", "Adelaide", -34.93, 138.60),
    ("TAS", "Hobart", -42.88, 147.33),
]
# Each city uses the nearest grid square that is >= 90% land (coastal squares read too cool).
# Manual picks where that lands somewhere unrepresentative:
CITY_SQUARE = {"Adelaide": (-34.75, 138.75)}   # nearest land square is in the cooler Adelaide Hills
LAND_MIN = 0.9

# W-027: wind and solar farm areas (MODELS.md). Taken from the same fields as the cities (no extra download), saved in
# data/farms/<feed>/<run>.parquet; the screen uses each state's average for wind (kind "wind") and solar ("solar").
FARMS = [  # (region, kind, area, lat, lon)
    ("NSW", "wind", "New England", -29.75, 151.35),
    ("NSW", "wind", "Central West", -32.47, 148.98),
    ("NSW", "wind", "Southern Tablelands", -34.75, 149.45),
    ("NSW", "solar", "Riverina (Darlington Pt)", -34.60, 146.05),
    ("NSW", "solar", "North West (Moree)", -29.45, 149.85),
    ("QLD", "wind", "Darling Downs (Coopers Gap)", -26.75, 151.45),
    ("QLD", "wind", "Far North (Mt Emerald)", -17.18, 145.38),
    ("QLD", "solar", "Western Downs", -26.85, 150.65),
    ("QLD", "solar", "North (Townsville)", -19.45, 146.75),
    ("VIC", "wind", "Western Vic (Ararat / Stockyard Hill)", -37.55, 143.25),
    ("VIC", "wind", "South Gippsland", -38.75, 145.95),
    ("VIC", "solar", "North West (Mildura / Kiamal)", -34.95, 142.25),
    ("SA", "wind", "Mid North (Hallett / Snowtown)", -33.60, 138.60),
    ("SA", "wind", "South East (Lake Bonney)", -37.75, 140.40),
    ("SA", "solar", "Port Augusta (Bungala)", -32.45, 137.85),
    ("SA", "solar", "Riverland", -34.20, 140.70),
]
# every point taken from each field: the cities first, then the farm areas
POINTS = [(r, c, la, lo) for r, c, la, lo in CITIES] + [(r, a, la, lo) for r, _, a, la, lo in FARMS]

# East-coast map box (degrees), 0.25 deg grid
GRID = dict(north=-9.0, south=-44.0, west=129.0, east=155.0)

# AWS copy first (faster), ECMWF server as backup
SOURCES = [
    "https://ecmwf-forecasts.s3.eu-central-1.amazonaws.com",
    "https://data.ecmwf.int/forecasts",
]
KEEP_DAYS = 4          # how far back ECMWF keeps runs
GRID_KEEP_DAYS = 30    # map data kept on disk

ALL_PARAMS = ["2t", "2d", "10u", "10v", "100u", "100v", "tcc", "tp", "ssrd"]
ENS_PARAMS = ["2t", "100u", "100v", "tp", "ssrd"]
# Highest / lowest temperature in the last 3 h (to day 6) or 6 h (after). Not in AIFS.
MAXMIN = {"mx2t3": "mx2t", "mx2t6": "mx2t", "mn2t3": "mn2t", "mn2t6": "mn2t"}


def _steps(*ranges):
    out = []
    for start, stop, by in ranges:
        out += list(range(start, stop + 1, by))
    return out


LONG = _steps((0, 144, 3), (150, 360, 6))        # 15 days
SHORT = _steps((0, 90, 3))                       # 06z/18z quick update
AI = _steps((0, 360, 6))
# 6-hourly to day 7, then 4 pm / 4 am AEST (06z / 18z UTC) to day 15
ENS = _steps((0, 168, 6), (174, 354, 12))
# W-022: the max/min-only steps the ensemble is missing, so every hour of every day is covered:
# 3-hourly windows to 144 h (ENS has the even ones), 6-hourly windows 168–360 h (ENS has 174, 186, …)
ENS_MAXMIN = _steps((3, 141, 6), (180, 360, 12))

FEEDS = {
    "ifs": dict(label="IFS main model", model="ifs", stream="oper", type="fc",
                params=ALL_PARAMS + list(MAXMIN), runs={0: LONG, 6: SHORT, 12: LONG, 18: SHORT}),
    "aifs": dict(label="AIFS AI model", model="aifs-single", stream="oper", type="fc",
                 params=ALL_PARAMS, runs={0: AI, 12: AI}),
    "ens": dict(label="IFS ensemble", model="ifs", stream="enfo", type="ef",
                params=ENS_PARAMS + list(MAXMIN), runs={0: ENS}),
    "ensx": dict(label="IFS ensemble max/min (extra steps)", model="ifs", stream="enfo", type="ef",
                 params=list(MAXMIN), runs={0: ENS_MAXMIN}),
}


def replace(tmp, dest):
    """os.replace with retries: Windows refuses the swap while another part of Weather is reading dest (22 Oct)."""
    import time
    for i in range(40):   # up to ~2 s
        try:
            return os.replace(tmp, dest)
        except PermissionError:
            if i == 39:
                raise
            time.sleep(0.05)
