"""Seasonal outlook (ECMWF SEAS5, months 1-6) from Copernicus, cut to the east coast on their server.

- Values are differences from normal ("anomalies"), all 51 members, 1 deg grid.
- Three models: ECMWF SEAS5 (feed "seasonal", out on the 5th), BOM ACCESS-S2 (feed "seasonal_bom", in the
  Copernicus multi-model set by the 10th) and NCEP CFSv2 (feed "seasonal_cfs", US, by the 13th). Same grid, same
  units, each vs its own 1993-2016 normal.
- Saved as data/cities/<feed>/<YYYYMM>.parquet (members) + data/grid/<feed>/<YYYYMM>.npz
  (mean, p10, p90, chance above normal). Raw download deleted after reading.
"""
from datetime import datetime, timedelta, timezone
import json
import logging
import os

import cdsapi
import eccodes
import numpy as np
import pandas as pd

from . import config as C, progress
from .ecmwf import _catalog_lock, load_catalog, _catalog_file

log = logging.getLogger("weather.seasonal")

DATASET = "seasonal-postprocessed-single-levels"
# feed -> (Copernicus centre, system, day of month it is out)
CENTRES = {"seasonal": ("ecmwf", "51", 5), "seasonal_bom": ("bom", "2", 10), "seasonal_cfs": ("ncep", "2", 13)}
NAMES = {"seasonal": "ECMWF SEAS5", "seasonal_bom": "BOM ACCESS-S2", "seasonal_cfs": "CFS (US)"}
LEADS = 6
# Copernicus variable -> (our name, multiplier by unit written in the file)
VARS = {
    "2m_temperature_anomaly": ("temp_anom_c", {"K": 1.0}),
    "total_precipitation_anomalous_rate_of_accumulation": ("rain_anom_mm_day", {"m s**-1": 86400 * 1000}),
    "10m_wind_speed_anomaly": ("wind10_anom_kmh", {"m s**-1": 3.6}),
    # file says "J m**-2" but values are a rate (typical +-12) -> W/m2
    "surface_solar_radiation_downwards_anomalous_rate_of_accumulation": ("solar_anom_wm2", {"W m**-2": 1.0, "J m**-2 s**-1": 1.0, "J m**-2": 1.0}),
}


def latest_issue(day=5, now=None):
    """Newest forecast month that is published (from `day` of the month, 12 UTC)."""
    now = now or datetime.now(timezone.utc)
    y, m = now.year, now.month
    if (now.day, now.hour) < (day, 12):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return y, m


def _read(path, scale_by_unit):
    """GRIB -> array (member, lead, lat, lon), lat, lon, valid months."""
    fields = {}
    with open(path, "rb") as f:
        while True:
            h = eccodes.codes_grib_new_from_file(f)
            if h is None:
                break
            try:
                g = lambda k: eccodes.codes_get(h, k)
                unit = g("units")
                if unit not in scale_by_unit:
                    raise ValueError(f"unexpected unit {unit!r} in {path.name}")
                ni, nj = g("Ni"), g("Nj")
                vals = eccodes.codes_get_values(h).reshape(nj, ni) * scale_by_unit[unit]
                lat = g("latitudeOfFirstGridPointInDegrees") - g("jDirectionIncrementInDegrees") * np.arange(nj)
                lon = g("longitudeOfFirstGridPointInDegrees") + g("iDirectionIncrementInDegrees") * np.arange(ni)
                # validity = END of the month's average (e.g. 1 Nov for October) -> label by the month itself
                end = datetime.strptime(str(g("validityDate")), "%Y%m%d")
                valid = (end - timedelta(days=1)).strftime("%Y%m")
                fields[(int(g("number")), valid)] = vals.astype(np.float32)
            finally:
                eccodes.codes_release(h)
    members = sorted({k[0] for k in fields})
    months = sorted({k[1] for k in fields})
    arr = np.full((len(members), len(months), nj, ni), np.nan, np.float32)
    for (m, v), a in fields.items():
        arr[members.index(m), months.index(v)] = a
    return arr, lat, lon, months, members


def get_issue(year, month, feed="seasonal"):
    centre, system, _ = CENTRES[feed]
    issue = f"{year}{month:02d}"
    raw = C.DATA / "raw" / "seasonal"
    raw.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client(quiet=True, progress=False)
    area = [C.GRID["north"], C.GRID["west"], C.GRID["south"], C.GRID["east"]]
    grid, rows, members = {}, None, []
    progress.start(f"Seasonal {NAMES[feed]} (Copernicus queue)", len(VARS), "", issue)
    for var, (name, scale) in VARS.items():
        target = raw / f"{feed}_{issue}_{name}.grib"
        if target.exists():   # kept from an earlier try
            log.info("%s %s: %s already downloaded", feed, issue, var)
        else:
            log.info("%s %s: requesting %s", feed, issue, var)
            try:
                client.retrieve(DATASET, {
                    "originating_centre": centre, "system": system, "variable": [var],
                    "product_type": ["monthly_mean"], "year": [str(year)], "month": [f"{month:02d}"],
                    "leadtime_month": [str(i) for i in range(1, LEADS + 1)],
                    "area": area, "data_format": "grib"}).download(str(target.with_suffix(".part")))
            except Exception as e:   # a model may not offer every field – leave it blank
                log.warning("%s %s: %s not available (%s)", feed, issue, var, str(e)[:150])
                continue
            C.replace(target.with_suffix(".part"), target)
        progress.step(target.stat().st_size)
        arr, lat, lon, months, members = _read(target, scale)

        q = np.nanpercentile(arr, [10, 90], axis=0)
        grid[f"{name}_mean"] = np.nanmean(arr, axis=0)
        grid[f"{name}_p10"], grid[f"{name}_p90"] = q[0], q[1]
        grid[f"{name}_chance_above"] = (arr > 0).mean(axis=0).astype(np.float32)   # 0-1

        # Cities: nearest 1 deg square (anomalies change slowly across space)
        pts = []
        for region, city, la, lo in C.CITIES:
            i, j = int(np.argmin(abs(lat - la))), int(np.argmin(abs(lon - lo)))
            for mi, mem in enumerate(members):
                for vi, vm in enumerate(months):
                    pts.append((region, city, mem, vm, float(arr[mi, vi, i, j])))
        df = pd.DataFrame(pts, columns=["region", "city", "member", "month", name])
        rows = df if rows is None else rows.merge(df, on=["region", "city", "member", "month"], how="outer")

    if rows is None:
        raise RuntimeError(f"{feed} {issue}: nothing downloaded")
    rows.insert(0, "issue", issue)
    rows["month"] = pd.to_datetime(rows["month"], format="%Y%m").dt.strftime("%Y-%m")
    out_c = C.DATA / "cities" / feed
    out_g = C.DATA / "grid" / feed
    out_c.mkdir(parents=True, exist_ok=True)
    out_g.mkdir(parents=True, exist_ok=True)
    rows.round(3).to_parquet(out_c / f"{issue}.parquet", index=False)
    with open(out_g / f"{issue}.npz", "wb") as f:
        np.savez_compressed(f, lat=lat.astype(np.float32), lon=lon.astype(np.float32),
                            months=np.array(pd.to_datetime(months, format="%Y%m").strftime("%Y-%m"), dtype="U7"), **grid)
    with _catalog_lock:
        cat = load_catalog()
        cat.setdefault(feed, {})[issue] = {
            "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"), "members": len(members)}
        tmp = _catalog_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, indent=1))
        C.replace(tmp, _catalog_file())
    for var, (name, _) in VARS.items():
        (raw / f"{feed}_{issue}_{name}.grib").unlink(missing_ok=True)
    log.info("%s %s done: %d members, months %s to %s", feed, issue, len(members), months[0], months[-1])


def update():
    """Fetch the newest seasonal forecast of each model if we don't have it yet (one model failing doesn't stop the others)."""
    errors = []
    for feed, (_, _, day) in CENTRES.items():
        y, m = latest_issue(day)
        if f"{y}{m:02d}" not in load_catalog().get(feed, {}):
            try:
                get_issue(y, m, feed)
            except Exception as e:
                log.exception("%s %d-%02d failed", feed, y, m)
                errors.append(f"{NAMES[feed]}: {str(e)[:150]}")
    if errors:
        raise RuntimeError("; ".join(errors))
