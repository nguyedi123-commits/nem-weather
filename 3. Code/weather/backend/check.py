"""F1 Forecast check (W-014, card F1): forecasts kept on this PC against what BOM measured at the city station.

Day N ahead = target day N days after the day the run started (NEM time); several runs that day -> the latest.
Measured (BOM Daily Weather Observations): high = 24 h from 9 am (same day), low = 24 h to 9 am (same day),
rain = 24 h to 9 am -> the figure recorded the NEXT morning belongs to the forecast day, sunshine hours.
Model values at the city square (not the W-027 farm areas), so they match the station.
"""
from datetime import date, datetime, timedelta, timezone
import glob
import logging

import numpy as np
import pandas as pd

from . import config as C, views
from .ecmwf import load_catalog, parse_run

log = logging.getLogger("weather.check")
REGIONS = ["NSW", "QLD", "VIC", "SA"]
LEADS = [1, 2, 3, 5, 7]
FEEDS = [("ifs", "IFS"), ("aifs", "AIFS"), ("ens", "Ensemble")]
MODELS = ["IFS", "AIFS", "Ensemble", "BOM"]
CHART_DAYS = 14
_cache = {}


def _today():
    return (datetime.now(timezone.utc) + timedelta(hours=10)).date()


def _city_frame(feed, rid):
    """A run's city table with the CITY sun (W-027 replaced it with the farm areas for the screen)."""
    df = views._cities.__wrapped__(feed, rid)   # not through the small cache: every run is read once here
    if "solar_wm2_city" in df:
        df = df.assign(solar_wm2=df["solar_wm2_city"])
        df["solar_kwh"] = df["solar_wm2"] * df["period_h"] / 1000
    return df


def _model_rows():
    rows = []
    for feed, name in FEEDS:
        for rid in views.runs(feed):
            try:
                df = _city_frame(feed, rid)
            except Exception as e:
                log.warning("check: %s %s skipped (%s)", feed, rid, e)
                continue
            start = (parse_run(rid) + timedelta(hours=10)).date()
            for r in REGIONS:
                x = df[df.region == r]
                if feed == "ens":
                    days = {d: (v["high"][1], v["low"][1], v["rain"][1], v["solar"][1]) for d, v in views._ens_daily(x).items()}
                else:
                    days = {d: (v["high"], v["low"], v["rain"], v["solar"])
                            for d, v in views._det_daily(x).items() if v["hours"] >= 20}
                for d, (hi, lo, rain, sun) in days.items():
                    lead = (date.fromisoformat(d) - start).days
                    if lead in LEADS:
                        rows.append((name, r, d, lead, rid, hi, lo, None if rain is None else rain >= 1, sun))
    return rows


def _bom_rows():
    rows = []
    for f in glob.glob(str(C.DATA / "cities" / "bom" / "*.parquet")):
        b = pd.read_parquet(f)
        for x in b.itertuples():
            if x.region not in REGIONS:
                continue
            issued = (pd.Timestamp(x.issue_utc) + pd.Timedelta(hours=10)).date()
            lead = (date.fromisoformat(x.date) - issued).days
            if lead in LEADS:
                rain = None if pd.isna(x.rain_chance) else x.rain_chance >= 50
                rows.append(("BOM", x.region, x.date, lead, x.issue_utc, x.high, x.low, rain, None))
    return rows


def _obs():
    """Measured, per region and forecast day: o_high, o_low, rain_mm (recorded the next morning), sun_hours."""
    o = pd.read_parquet(C.DATA / "obs" / "daily.parquet")
    o["date"] = o["date"].astype(str)
    nxt = o[["region", "date", "rain_mm"]].copy()   # rain recorded the next morning belongs to the day before
    nxt["date"] = (pd.to_datetime(nxt["date"]) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    obs = o[["region", "date", "high", "low", "sun_hours"]].merge(nxt, on=["region", "date"], how="left")
    return obs.rename(columns={"high": "o_high", "low": "o_low"})


def _table(obs):
    cols = ["model", "region", "date", "lead", "run", "high", "low", "rain", "sun"]
    df = pd.DataFrame(_model_rows() + _bom_rows(), columns=cols)
    df = df.sort_values("run").drop_duplicates(["model", "region", "date", "lead"], keep="last")   # latest run that day
    return df.merge(obs, on=["region", "date"], how="left")


def _scores(x):
    out = {}
    for k in ("high", "low"):
        e = (pd.to_numeric(x[k], errors="coerce") - x[f"o_{k}"]).dropna()
        out[k] = {"n": int(len(e)), "miss": round(float(e.abs().mean()), 1) if len(e) else None,
                  "lean": round(float(e.mean()), 1) if len(e) else None}
    r = x[x["rain"].notna() & x["rain_mm"].notna()]
    out["rain"] = {"n": int(len(r)), "right": round(float(((r["rain"].astype(bool)) == (r["rain_mm"] >= 1)).mean() * 100))
                   if len(r) else None}
    s = x[pd.to_numeric(x["sun"], errors="coerce").notna() & x["sun_hours"].notna()]
    c = np.corrcoef(s["sun"].astype(float), s["sun_hours"].astype(float))[0, 1] if len(s) >= 5 else np.nan
    out["sun"] = {"n": int(len(s)), "match": None if np.isnan(c) else round(float(max(c, 0)) * 100)}
    return out


def check(period="30"):
    period = int(period) if str(period).isdigit() else 30
    cat = C.DATA / "catalog.json"
    key = (cat.stat().st_mtime if cat.exists() else 0, (C.DATA / "obs" / "daily.parquet").stat().st_mtime
           if (C.DATA / "obs" / "daily.parquet").exists() else 0, _today(), period)
    if key in _cache:
        return _cache[key]
    if not (C.DATA / "obs" / "daily.parquet").exists():
        return {"error": "No BOM measurements yet – they come with the cloud data (obs)."}
    obs = _obs()
    t = _table(obs)
    today = _today()
    first = (today - timedelta(days=period)).isoformat()
    t = t[(t["date"] >= first) & (t["date"] < today.isoformat())]
    chart_days = [(today - timedelta(days=k)).isoformat() for k in range(CHART_DAYS, 0, -1)]
    out = {"period": period, "leads": LEADS, "models": MODELS, "regions": {}}
    for r in REGIONS:
        x = t[t["region"] == r]
        table = {m: {str(l): _scores(x[(x["model"] == m) & (x["lead"] == l)]) for l in LEADS} for m in MODELS}
        d1 = x[x["lead"] == 1].set_index(["model", "date"])
        ob = obs[obs["region"] == r].set_index("date")
        pick = lambda col, m, d: (None if (m, d) not in d1.index or pd.isna(d1.loc[(m, d), col]) else
                                  (bool(d1.loc[(m, d), col]) if col == "rain" else round(float(d1.loc[(m, d), col]), 1)))
        obs_v = lambda col, d: None if d not in ob.index or pd.isna(ob.loc[d, col]) else round(float(ob.loc[d, col]), 1)
        out["regions"][r] = {
            "city": views.CITY[r], "table": table, "days": int(x["date"].nunique()),
            "sun_measured": bool(ob["sun_hours"].notna().any()),
            "chart": {"dates": chart_days, "labels": [views._day_label(d)[:6] for d in chart_days],
                      "obs": {k: [obs_v(c, d) for d in chart_days] for k, c in
                              (("high", "o_high"), ("low", "o_low"), ("rain", "rain_mm"), ("sun", "sun_hours"))},
                      "models": {m: {k: [pick(k, m, d) for d in chart_days] for k in ("high", "low", "rain", "sun")}
                                 for m in MODELS}}}
    _cache.clear()
    _cache[key] = out
    return out
