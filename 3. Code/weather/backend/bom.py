"""BOM city forecasts – the forecast BOM publishes for each capital (precis XML on BOM's FTP).

Per day, 7 days: high, low, rain range (mm), chance of rain, short words ("Partly cloudy.").
A few KB per refresh. Every issue is kept (data/cities/bom/<issue>.parquet) – useful later to check BOM vs ECMWF.
"""
from datetime import datetime, timezone
import json
import logging
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

from . import config as C
from .ecmwf import _catalog_lock, load_catalog, _catalog_file

log = logging.getLogger("weather.bom")

URL = "ftp://ftp.bom.gov.au/anon/gen/fwo/{}.xml"
PRODUCTS = {"QLD": "IDQ11295", "NSW": "IDN11060", "VIC": "IDV10753", "SA": "IDS10044", "TAS": "IDT16710"}


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def _read(region, city, xml_bytes):
    root = ET.fromstring(xml_bytes)
    issue = root.findtext("amoc/issue-time-utc")
    area = next(a for a in root.iter("area") if a.get("description") == city and a.get("type") == "location")
    rows = []
    for p in area.iter("forecast-period"):
        v = {e.get("type"): (e.text or "").strip() for e in p}
        mm = [float(x) for x in re.findall(r"[\d.]+", v.get("precipitation_range", ""))]
        rows.append({
            "issue_utc": issue, "region": region, "city": city, "date": p.get("start-time-local")[:10],
            "high": _num(v.get("air_temperature_maximum")), "low": _num(v.get("air_temperature_minimum")),
            "rain_lo": mm[0] if mm else float("nan"), "rain_hi": mm[-1] if mm else float("nan"),
            "rain_chance": _num(v.get("probability_of_precipitation", "").rstrip("%")),
            "words": v.get("precis", ""),
        })
    return issue, rows


def update():
    """Fetch BOM's latest city forecasts (always – tiny). Saved under the newest issue time."""
    rows, issues = [], []
    for region, city in ((r, c) for r, c, *_ in C.CITIES):
        with urllib.request.urlopen(URL.format(PRODUCTS[region]), timeout=60) as r:
            issue, rs = _read(region, city, r.read())
        issues.append(issue)
        rows += rs
    key = max(issues).replace("-", "").replace("T", "").replace(":", "")[:12]   # YYYYMMDDHHMM (UTC)
    out = C.DATA / "cities" / "bom"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out / f"{key}.parquet", index=False)
    with _catalog_lock:
        cat = load_catalog()
        cat.setdefault("bom", {})[key] = {"finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                          "issued_utc": max(issues)}
        tmp = _catalog_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, indent=1))
        os.replace(tmp, _catalog_file())
    log.info("BOM city forecasts: issue %s, %d rows", max(issues), len(rows))
