"""BOM observations – what actually happened at each city's station (W-008: later used to correct ECMWF).

Two BOM sources, both tiny, fetched on every refresh and merged into one history (never deleted):
- Daily Weather Observations (monthly CSV, whole month so far): daily low, high, rain, sunshine hours, max gust.
  We read this month and last month, so a refresh weeks apart still fills every day.
  BOM convention: low = 24 h to 9 am on that date, high = 24 h from 9 am, rain = 24 h to 9 am.
- Latest observations (JSON, every 30 min, last ~3 days): temperature, humidity, wind, cloud.
Saved: data/obs/daily.parquet and data/obs/halfhourly.parquet.
"""
from datetime import datetime, timezone
import io
import json
import logging
import os
import urllib.request

import pandas as pd

from . import config as C
from .ecmwf import _catalog_lock, load_catalog, _catalog_file

log = logging.getLogger("weather.obs")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}   # BOM refuses requests without one
# region -> (station name, daily CSV code, latest-obs JSON product)
STATIONS = {
    "QLD": ("Brisbane", "IDCJDW4019", "IDQ60901/IDQ60901.94576"),
    "NSW": ("Sydney (Observatory Hill)", "IDCJDW2124", "IDN60901/IDN60901.94768"),
    "VIC": ("Melbourne (Olympic Park)", "IDCJDW3033", "IDV60901/IDV60901.95936"),
    "SA": ("Adelaide (West Terrace)", "IDCJDW5081", "IDS60901/IDS60901.94648"),
    "TAS": ("Hobart (Ellerslie Road)", "IDCJDW7021", "IDT60901/IDT60901.94970"),
}
DAILY_COLS = {"Minimum temperature": "low", "Maximum temperature": "high", "Rainfall": "rain_mm",
              "Sunshine": "sun_hours", "Speed of maximum wind gust": "gust_kmh"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def _daily_month(region, code, month):
    text = _get(f"https://www.bom.gov.au/climate/dwo/{month}/text/{code}.{month}.csv").decode("latin-1")
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if '"Date"' in l)
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    out = pd.DataFrame({"region": region, "date": pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")})
    for col in df.columns:
        for key, name in DAILY_COLS.items():
            if str(col).startswith(key):
                out[name] = pd.to_numeric(df[col], errors="coerce")
    return out


def _merge(path, new, keys):
    """Add new rows to the history; a newer reading of the same key replaces the old one."""
    if path.exists():
        new = pd.concat([pd.read_parquet(path), new]).drop_duplicates(keys, keep="last")
    new = new.sort_values(keys).reset_index(drop=True)
    tmp = path.with_suffix(".tmp")
    new.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    return new


def update():
    out = C.DATA / "obs"
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    this = now.strftime("%Y%m")
    last = (now.replace(day=1) - pd.Timedelta(days=1)).strftime("%Y%m")
    daily, half, problems = [], [], []
    for region, (name, code, product) in STATIONS.items():
        for month in (last, this):
            try:
                daily.append(_daily_month(region, code, month))
            except Exception as e:
                problems.append(f"{region} daily {month}: {e}")
        try:
            data = json.loads(_get(f"https://www.bom.gov.au/fwo/{product}.json"))["observations"]["data"]
            h = pd.DataFrame(data)
            half.append(pd.DataFrame({
                "region": region, "time_utc": pd.to_datetime(h["aifstime_utc"], format="%Y%m%d%H%M%S"),
                "temp_c": pd.to_numeric(h["air_temp"], errors="coerce"),
                "humidity_pct": pd.to_numeric(h["rel_hum"], errors="coerce"),
                "wind_kmh": pd.to_numeric(h["wind_spd_kmh"], errors="coerce"),
                "cloud_oktas": pd.to_numeric(h["cloud_oktas"], errors="coerce"),
                "rain_since_9am_mm": pd.to_numeric(h["rain_trace"], errors="coerce")}))
        except Exception as e:
            problems.append(f"{region} latest: {e}")
    d = _merge(out / "daily.parquet", pd.concat(daily), ["region", "date"]) if daily else None
    hh = _merge(out / "halfhourly.parquet", pd.concat(half), ["region", "time_utc"]) if half else None
    with _catalog_lock:
        cat = load_catalog()
        cat["obs"] = {"updated": now.isoformat(timespec="seconds"),
                      "daily_days": int(d["date"].nunique()) if d is not None else 0,
                      "first_day": d["date"].min() if d is not None else None,
                      "halfhourly_rows": int(len(hh)) if hh is not None else 0, "problems": problems}
        tmp = _catalog_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, indent=1))
        os.replace(tmp, _catalog_file())
    for p in problems:
        log.warning("BOM observations: %s", p)
    log.info("BOM observations: %s days of daily records, %s half-hourly readings",
             cat["obs"]["daily_days"], cat["obs"]["halfhourly_rows"])
