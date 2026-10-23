"""Turn saved data (data/cities, data/grid) into the small JSON each panel needs. No downloads here.

All times are NEM time (AEST = UTC+10, no daylight saving), sent as "YYYY-MM-DDTHH:MM".
Run choice (W-017): every view takes run ("latest" or a run id) and vs ("auto" = same time yesterday, else the run
before; "none"; or a run id). The vs run comes back inside the same answer, matched by time / day / month.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config as C
from .ecmwf import load_catalog, parse_run, run_id

AEST = pd.Timedelta(hours=10)
REGIONS = [r for r, *_ in C.CITIES]
CITY = {r: c for r, c, *_ in C.CITIES}
FEED_LABEL = {"ifs": "IFS main model", "aifs": "AIFS AI model", "ens": "IFS ensemble (50 runs)",
              "bom": "BOM city forecasts", "seasonal": "ECMWF SEAS5 seasonal (51 runs)",
              "seasonal_bom": "BOM ACCESS-S2 seasonal (110 runs)", "seasonal_cfs": "CFS (US) seasonal"}
DAILY_KEYS = ("high", "low", "rain", "solar", "wind")


# ---------- helpers ----------

def _num(a, d=1):
    """Array -> JSON list, NaN -> None."""
    a = np.round(np.asarray(a, dtype=float), d)
    return [None if np.isnan(v) else float(v) for v in a]


def _iso(ts):
    return [t.strftime("%Y-%m-%dT%H:%M") for t in pd.to_datetime(ts)]


def _clean_num(v, d=1):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), d)


def runs(feed):
    """Finished runs of a feed, newest first."""
    return sorted(load_catalog().get(feed, {}), reverse=True)


def latest(feed):
    r = runs(feed)
    return r[0] if r else None


def latest_long(feed):
    """Newest 15-day run (00z / 12z). IFS 06z / 18z only go to 90 h – fine for Short, too short for Medium / AI vs IFS."""
    r = [x for x in runs(feed) if x[-2:] in ("00", "12")]
    return r[0] if r else None


def _run_aest(rid):
    return (parse_run(rid) + timedelta(hours=10)).strftime("%a %d %b %H:%M")


def run_text(feed, rid):
    if not rid:
        return None
    if feed.startswith("seasonal"):
        return datetime.strptime(rid, "%Y%m").strftime("%B %Y")
    if feed == "bom":
        return (datetime.strptime(rid, "%Y%m%d%H%M") + timedelta(hours=10)).strftime("%a %d %b %H:%M")
    return _run_aest(rid)


def _grid_file(feed, rid):
    return C.DATA / "grid" / feed / f"{rid}.npz"


def resolve(feed, run="latest", vs="auto", have=None):
    """(run id, vs id) for a feed. have = the runs that can be used (default: all finished runs)."""
    lst = have if have is not None else runs(feed)
    if not lst:
        return None, None
    rid = run if run in lst else lst[0]
    older = [x for x in lst if x < rid]
    if vs in (None, "", "auto"):
        if feed.startswith("seasonal"):
            vid = older[0] if older else None
        else:
            day_before = run_id(parse_run(rid) - timedelta(hours=24))
            vid = day_before if day_before in lst else (older[0] if older else None)
    elif vs == "none":
        vid = None
    else:
        vid = vs if vs in lst and vs != rid else None
    return rid, vid


def runs_view():
    """Run lists for the run / vs pickers (city data: all runs; maps: runs with a map file, 30 days)."""
    out = {}
    for feed in ("ifs", "aifs", "ens", "seasonal", "seasonal_cfs"):
        lst = runs(feed)
        out[feed] = [{"id": r, "text": run_text(feed, r), "map": _grid_file(feed, r).exists()} for r in lst]
    return out


@lru_cache(maxsize=32)
def _cities(feed, rid):
    df = pd.read_parquet(C.DATA / "cities" / feed / f"{rid}.parquet")
    df["t"] = df["valid_utc"] + AEST
    for col in ("tmax_c", "tmin_c"):   # files saved before 18 Oct fix had zeros (-273) at 0 h
        if col in df:
            df.loc[df["step_h"] == 0, col] = np.nan
    if feed == "ens":   # W-022: add the extra max/min-only steps, so daily highs / lows cover all 24 hours
        fx = C.DATA / "cities" / "ensx" / f"{rid}.parquet"
        if fx.exists():
            x = pd.read_parquet(fx)
            x["t"] = x["valid_utc"] + AEST
            df = pd.concat([df, x], ignore_index=True).sort_values(["city", "member", "step_h"], ignore_index=True)
    # period length from the previous step that has the full fields (extra max/min rows don't count as periods)
    full = df["temp_c"].notna() if "temp_c" in df else pd.Series(True, index=df.index)
    keys = ["city"] + (["member"] if "member" in df else [])
    df["period_h"] = np.nan
    df.loc[full, "period_h"] = df[full]["step_h"] - df[full].groupby(keys)["step_h"].shift()
    df["solar_kwh"] = df["solar_wm2"] * df["period_h"] / 1000
    df["pday"] = (df["t"] - pd.Timedelta(minutes=1)).dt.normalize()   # day a period (or max/min window) belongs to
    df["iday"] = df["t"].dt.normalize()                                 # day of an instant value
    return df


def _daily(x, keys=()):
    """Daily high / low / rain / sun / wind for one city (and per member if keys=("member",))."""
    g = list(keys)
    has_mx = "tmax_c" in x and x["tmax_c"].notna().any()
    per = x.groupby(g + ["pday"]).agg(hours=("period_h", "sum"), rain=("rain_mm", "sum"), solar=("solar_kwh", "sum"),
                                      **({"high": ("tmax_c", "max"), "low": ("tmin_c", "min")} if has_mx else {}))
    inst = x.groupby(g + ["iday"]).agg(wind=("wind100_kmh", "mean"),
                                       **({} if has_mx else {"high": ("temp_c", "max"), "low": ("temp_c", "min")}))
    inst.index = inst.index.set_names(g + ["pday"])
    return per.join(inst, how="outer").reset_index().rename(columns={"pday": "day"})


def _ens_daily(x):
    """Ensemble, one city: date -> {high/low/rain/solar/wind: [p10, p50, p90], rain_chance} (full days only)."""
    dm = _daily(x, ("member",))
    out = {}
    for day, v in dm.groupby("day"):
        if v["hours"].median() < 20:
            continue
        row = {k: [round(float(a), 1) for a in np.nanpercentile(v[k], [10, 50, 90])] for k in DAILY_KEYS}
        row["rain_chance"] = round(float((v["rain"] >= 1).mean() * 100))
        out[pd.Timestamp(day).strftime("%Y-%m-%d")] = row
    return out


def _det_daily(x):
    """Single run, one city: date -> {high, low, rain, solar, wind, hours}."""
    return {pd.Timestamp(r.day).strftime("%Y-%m-%d"): {**{k: _clean_num(getattr(r, k)) for k in DAILY_KEYS},
                                                      "hours": float(r.hours)} for r in _daily(x).itertuples()}


def _day_label(d):
    return pd.Timestamp(d).strftime("%a %d %b")


def _quant(x, col, by):
    x = x[x[col].notna()]   # the extra max/min-only rows have no temperature etc.
    return x.groupby(by)[col].quantile([0.1, 0.5, 0.9]).unstack()


def bom_days():
    """Latest BOM city forecast: region -> {"YYYY-MM-DD": {high, low, rain_lo, rain_hi, chance, words}}."""
    rid = latest("bom")
    if not rid:
        return None, {}
    df = pd.read_parquet(C.DATA / "cities" / "bom" / f"{rid}.parquet")
    out = {r: {} for r in REGIONS}
    for row in df.itertuples():
        out[row.region][row.date] = {"high": _clean_num(row.high, 0), "low": _clean_num(row.low, 0),
                                     "rain_lo": _clean_num(row.rain_lo, 0), "rain_hi": _clean_num(row.rain_hi, 0),
                                     "chance": _clean_num(row.rain_chance, 0), "words": row.words}
    return run_text("bom", rid), out


def _bom_marks(days):
    return [{"date": d, "high": v["high"], "low": v["low"]} for d, v in sorted(days.items())]


def _same_or_latest(feed, rid, main_feed, long=False):
    """Partner run for an older main run: the same run id if on disk; for the newest main run: the newest partner
    (long=True: the newest 15-day partner)."""
    if rid == latest(main_feed):
        return latest_long(feed) if long else latest(feed)
    return rid if rid in runs(feed) else None


# ---------- status ----------

def status():
    now = datetime.now(timezone.utc)
    feeds = []
    for feed in ("ifs", "aifs", "ens", "bom", "seasonal", "seasonal_bom", "seasonal_cfs"):
        rid = latest(feed)
        if not rid:
            feeds.append({"feed": feed, "label": FEED_LABEL[feed], "run": None})
            continue
        if feed == "bom":
            t = datetime.strptime(rid, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        elif feed.startswith("seasonal"):
            t = datetime.strptime(rid + "05", "%Y%m%d").replace(tzinfo=timezone.utc)
        else:
            t = parse_run(rid)
        feeds.append({"feed": feed, "label": FEED_LABEL[feed], "run": rid,
                      "run_text": run_text(feed, rid) + (" forecast" if feed.startswith("seasonal") else ""),
                      "age_h": round((now - t).total_seconds() / 3600)})
    mtime = (C.DATA / "catalog.json").stat().st_mtime if (C.DATA / "catalog.json").exists() else 0
    return {"feeds": feeds, "version": mtime,
            "now": (now + timedelta(hours=10)).strftime("%a %d %b %H:%M"),
            "regions": [{"region": r, "city": CITY[r]} for r in REGIONS]}


# ---------- S1 Short: IFS, next 3 days ----------

def short(run="latest", vs="auto"):
    rid, vid = resolve("ifs", run, vs)
    if not rid:
        return {"error": "No IFS data yet – click Refresh (top right)."}
    df = _cities("ifs", rid)
    re_, ra = _same_or_latest("ens", rid, "ifs"), _same_or_latest("aifs", rid, "ifs")
    ens = _cities("ens", re_) if re_ else None
    ai = _cities("aifs", ra) if ra else None
    old = _cities("ifs", vid) if vid else None
    bom_issued, bom = bom_days()
    out = {"run": rid, "run_text": _run_aest(rid), "vs": vid, "vs_text": run_text("ifs", vid),
           "ens_run": run_text("ens", re_), "aifs_run": run_text("aifs", ra), "bom_issued": bom_issued, "regions": {}}
    for r in REGIONS:
        x = df[df.region == r].sort_values("step_h")
        s = x[x.step_h <= 72]
        t0, t1 = s.t.min(), s.t.max()
        extra = {"bom_marks": _bom_marks(bom.get(r, {}))}
        chance = {}
        if ens is not None:
            e = ens[ens.region == r]
            w = e[(e.t >= t0) & (e.t <= t1)]
            if len(w):
                band = {}
                for key, col in (("temp", "temp_c"), ("wind", "wind100_kmh"), ("solar", "solar_wm2")):
                    q = _quant(w, col, "t")
                    d_ = 0 if key == "solar" else 1
                    band[key] = {"p10": _num(q[0.1], d_), "p90": _num(q[0.9], d_)}
                times = _quant(w, "temp_c", "t").index
                ph = w.groupby("t")["period_h"].first().reindex(times).fillna(0)
                band["time"] = _iso(times)
                band["time_mid"] = _iso(times - pd.to_timedelta(ph.values / 2, unit="h"))
                extra["band"] = band
            chance = {d: v["rain_chance"] for d, v in _ens_daily(e).items()}
        if ai is not None:
            y = ai[(ai.region == r) & (ai.t >= t0) & (ai.t <= t1)].sort_values("step_h")
            extra["aifs"] = {"time": _iso(y.t), "temp": _num(y.temp_c), "wind": _num(y.wind100_kmh)}
        if old is not None:   # the vs run over the same 3 days
            o = old[old.region == r].sort_values("step_h")
            w = o[(o.t >= t0) & (o.t <= t1)]
            extra["vs"] = {"time": _iso(w.t), "time_mid": _iso(w.t - pd.to_timedelta(w.period_h.fillna(0) / 2, unit="h")),
                           "temp": _num(w.temp_c), "wind": _num(w.wind100_kmh), "solar": _num(w.solar_wm2, 0),
                           "rain": _num(w.rain_mm), "daily": _det_daily(o)}
        d = _daily(x)
        first = d["day"].min()
        d = d[d["day"] < first + pd.Timedelta(days=4)]
        out["regions"][r] = {
            "city": CITY[r], "time": _iso(s.t),
            "time_mid": _iso(s.t - pd.to_timedelta(s.period_h.fillna(0) / 2, unit="h")),   # for period averages
            "temp": _num(s.temp_c), "wind": _num(s.wind100_kmh), "solar": _num(s.solar_wm2, 0),
            "rain": _num(s.rain_mm), "cloud": _num(s.cloud_pct, 0), "wind_dir": _num(s.wind100_dir, 0),
            "daily": [{"day": _day_label(row.day), "date": row.day.strftime("%Y-%m-%d"), "part": bool(row.hours < 20),
                       "high": _clean_num(row.high), "low": _clean_num(row.low), "rain": _clean_num(row.rain),
                       "wind": _clean_num(row.wind, 0), "solar": _clean_num(row.solar),
                       "rain_chance": chance.get(row.day.strftime("%Y-%m-%d")),
                       "bom": bom.get(r, {}).get(row.day.strftime("%Y-%m-%d"))} for row in d.itertuples()],
            **extra,
        }
    return out


# ---------- M1 Medium: ensemble range + IFS + AIFS, 15 days ----------

def _ens_series(x):
    out = {}
    for key, col in (("temp", "temp_c"), ("wind", "wind100_kmh")):
        q = _quant(x, col, "t")
        out[key] = {"p10": _num(q[0.1]), "p50": _num(q[0.5]), "p90": _num(q[0.9])}
    out["time"] = _iso(_quant(x, "temp_c", "t").index)
    return out


def medium(run="latest", vs="auto"):
    rid, vid = resolve("ens", run, vs)
    if not rid:
        return {"error": "No ensemble data yet – click Refresh (top right)."}
    ens = _cities("ens", rid)
    old = _cities("ens", vid) if vid else None
    part = {f: _same_or_latest(f, rid, "ens", long=True) for f in ("ifs", "aifs")}
    det = {f: (_cities(f, p) if p else None) for f, p in part.items()}
    bom_issued, bom = bom_days()
    out = {"run": rid, "run_text": _run_aest(rid), "vs": vid, "vs_text": run_text("ens", vid), "bom_issued": bom_issued,
           "runs": {f: run_text(f, p) for f, p in part.items()}, "regions": {}}
    for r in REGIONS:
        x = ens[ens.region == r]
        dets = {f: _det_daily(df[df.region == r]) for f, df in det.items() if df is not None}
        daily = []
        for date, row in _ens_daily(x).items():
            row = {"day": _day_label(date), "date": date, **row, "bom": bom.get(r, {}).get(date)}
            for f, dd in dets.items():
                v = dd.get(date)
                if v and v["hours"] >= 20:
                    row[f] = {k: v[k] for k in DAILY_KEYS}
            daily.append(row)
        lines = {}
        for f, df in det.items():
            if df is not None:
                y = df[df.region == r].sort_values("step_h")
                lines[f] = {"time": _iso(y.t), "temp": _num(y.temp_c), "wind": _num(y.wind100_kmh)}
        reg = {"city": CITY[r], **_ens_series(x), "lines": lines, "daily": daily, "bom_marks": _bom_marks(bom.get(r, {}))}
        if old is not None:
            o = old[old.region == r]
            reg["vs"] = {**_ens_series(o), "daily": _ens_daily(o)}
        out["regions"][r] = reg
    return out


# ---------- C1 AI vs IFS ----------

def compare():
    ri, ra = latest_long("ifs"), latest_long("aifs")
    if not (ri and ra):
        return {"error": "Need both IFS and AIFS data – click Refresh (top right)."}
    i, a = _cities("ifs", ri), _cities("aifs", ra)
    out = {"runs": {"ifs": _run_aest(ri), "aifs": _run_aest(ra)}, "regions": {}}
    for r in REGIONS:
        xi, xa = i[i.region == r].sort_values("step_h"), a[a.region == r].sort_values("step_h")
        di, da = _daily(xi), _daily(xa)
        both = di.merge(da, on="day", suffixes=("_ifs", "_ai"))
        both = both[(both.hours_ifs >= 20) & (both.hours_ai >= 20)]
        reg = {"city": CITY[r]}
        for f, y in (("ifs", xi), ("aifs", xa)):
            reg[f] = {"time": _iso(y.t), "time_mid": _iso(y.t - pd.to_timedelta(y.period_h.fillna(0) / 2, unit="h")),
                      "temp": _num(y.temp_c), "wind": _num(y.wind100_kmh),
                      "solar": _num(y.solar_wm2, 0), "rain": _num(y.rain_mm / y.period_h, 2)}
        reg["daily"] = [{"day": _day_label(b.day),
                         **{k: [round(getattr(b, f"{k}_ifs"), 1), round(getattr(b, f"{k}_ai"), 1)]
                            for k in DAILY_KEYS}} for b in both.itertuples()]
        out["regions"][r] = reg
    return out


# ---------- L1 Seasonal ----------

SEAS_COLS = {"temp": "temp_anom_c", "rain": "rain_anom_mm_day", "wind": "wind10_anom_kmh", "solar": "solar_anom_wm2"}


def _seas_stats(x):
    months = sorted(x.month.unique())
    reg = {"months": [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months]}
    for key, col in SEAS_COLS.items():
        if col not in x or x[col].isna().all():
            continue
        g = x.groupby("month")[col]
        q = g.quantile([0.1, 0.9]).unstack()
        reg[key] = {"mean": _num(g.mean(), 2), "p10": _num(q[0.1], 2), "p90": _num(q[0.9], 2),
                    "above": _num(g.apply(lambda v: (v.dropna() > 0).mean() * 100), 0)}
    return reg


def _seas_read(feed, rid):
    return pd.read_parquet(C.DATA / "cities" / feed / f"{rid}.parquet") if rid else None


def _issue_for(feed, rid):
    """BOM / CFS seasonal issue that goes with an ECMWF issue: the same month, else the newest one before it."""
    lst = [x for x in runs(feed) if x <= rid] if rid else []
    return lst[0] if lst else None


OTHERS = (("bom", "seasonal_bom"), ("cfs", "seasonal_cfs"))   # shown beside ECMWF on L1


def seasonal(run="latest", vs="auto"):
    rid, vid = resolve("seasonal", run, vs)
    if not rid:
        return {"error": "No seasonal data yet – click Refresh (top right)."}
    df, old = _seas_read("seasonal", rid), _seas_read("seasonal", vid)
    out = {"issue": rid, "issue_text": run_text("seasonal", rid), "vs": vid, "vs_text": run_text("seasonal", vid), "regions": {}}
    other = {}
    for key, feed in OTHERS:
        cur = _issue_for(feed, rid)
        was = _issue_for(feed, vid) if vid else None
        other[key] = (_seas_read(feed, cur), _seas_read(feed, was) if was and was != cur else None)
        out[f"{key}_issue_text"] = run_text(feed, cur)
    brief = lambda st: {"months": st["months"], **{k: {"mean": v["mean"], "above": v["above"]} for k, v in st.items() if k != "months"}}
    for r in REGIONS:
        reg = {"city": CITY[r], **_seas_stats(df[df.region == r])}
        for key, (cur, was) in other.items():
            if cur is not None:
                b = _seas_stats(cur[cur.region == r])
                reg[key] = {k: v for k, v in b.items() if k != "months"} if b["months"] == reg["months"] else {}
        if old is not None:   # by month name, so the caller can line months up
            reg["vs"] = brief(_seas_stats(old[old.region == r]))
            for key, (cur, was) in other.items():
                if was is not None:
                    reg[f"vs_{key}"] = brief(_seas_stats(was[was.region == r]))
        out["regions"][r] = reg
    return out


# ---------- D1 What changed ----------

LIMITS = {"high": 2.0, "low": 2.0, "rain": 5.0, "rain_chance": 30.0, "wind": 10.0, "solar": 1.5}
WHAT = {"high": ("High", "°C", 1), "low": ("Low", "°C", 1), "rain": ("Rain", "mm", 1), "rain_chance": ("Rain chance", "%", 0),
        "wind": ("Wind", "km/h", 0), "solar": ("Sun", "kWh/m²", 1)}


def changes(model="ens", run="latest", vs="auto"):
    feed = model if model in ("ifs", "aifs", "ens") else "ens"
    rid, vid = resolve(feed, run, vs)
    if not rid:
        return {"error": f"No {FEED_LABEL[feed]} data yet – click Refresh (top right)."}
    out = {"model": feed, "label": FEED_LABEL[feed], "run": rid, "run_text": run_text(feed, rid),
           "vs": vid, "vs_text": run_text(feed, vid), "rows": []}
    if not vid:
        out["note"] = "No earlier run on disk to compare with yet – each refresh adds one."
        return out
    new, old = _cities(feed, rid), _cities(feed, vid)
    for r in REGIONS:
        if feed == "ens":
            a, b = _ens_daily(new[new.region == r]), _ens_daily(old[old.region == r])
            mid = lambda d: {**{k: d[k][1] for k in DAILY_KEYS}, "rain_chance": d["rain_chance"]}
            a, b = {k: mid(v) for k, v in a.items()}, {k: mid(v) for k, v in b.items()}
        else:
            a = {k: v for k, v in _det_daily(new[new.region == r]).items() if v["hours"] >= 20}
            b = {k: v for k, v in _det_daily(old[old.region == r]).items() if v["hours"] >= 20}
        for date in sorted(set(a) & set(b)):
            items = []
            for k, lim in LIMITS.items():
                n, o = a[date].get(k), b[date].get(k)
                if n is None or o is None or abs(n - o) < lim:
                    continue
                name, unit, dp = WHAT[k]
                items.append({"what": name, "old": round(o, dp), "new": round(n, dp), "change": round(n - o, dp),
                              "unit": unit, "big": abs(n - o) >= 2 * lim})
            if items:
                out["rows"].append({"region": r, "city": CITY[r], "date": date, "day": _day_label(date), "items": items})
    out["rows"].sort(key=lambda x: (x["date"], REGIONS.index(x["region"])))
    return out


# ---------- G1 Map ----------

MAP_FIELDS = {
    "temp": {"det": "temp_c", "ens": "temp_c_p50", "seasonal": "temp_anom_c_mean"},
    "wind": {"det": "wind100_kmh", "ens": "wind100_kmh_p50", "seasonal": "wind10_anom_kmh_mean"},
    "solar": {"det": "solar_wm2", "ens": "solar_wm2_p50", "seasonal": "solar_anom_wm2_mean"},
    "rain": {"det": "rain_mm", "ens": "rain_mm_p50", "seasonal": "rain_anom_mm_day_mean"},
}


@lru_cache(maxsize=1)
def coastline():
    """Land/sea edge as short line pieces, from ECMWF's land-sea mask (marching squares at 50% land)."""
    f = C.DATA / "static" / "lsm.npz"
    if not f.exists():
        return []
    with np.load(f) as z:   # closed straight away, so the cloud pick-up can replace the file
        lat, lon, m = z["lat"], z["lon"], z["lsm"]
    segs = []
    land = m >= 0.5

    def edge(i1, j1, i2, j2):
        a, b = m[i1, j1], m[i2, j2]
        w = (0.5 - a) / (b - a) if b != a else 0.5
        return [round(float(lon[j1] + w * (lon[j2] - lon[j1])), 3), round(float(lat[i1] + w * (lat[i2] - lat[i1])), 3)]

    for i in range(len(lat) - 1):
        for j in range(len(lon) - 1):
            c = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            pts = []
            for k in range(4):
                p, q = c[k], c[(k + 1) % 4]
                if land[p] != land[q]:
                    pts.append(edge(*p, *q))
            if len(pts) == 2:
                segs.append(pts)
            elif len(pts) == 4:
                segs += [pts[:2], pts[2:]]
    return segs


@lru_cache(maxsize=8)
def _grid(feed, rid):
    with np.load(_grid_file(feed, rid)) as z:
        return {k: z[k] for k in z.files}


def _map_values(src, g, field, i):
    seas = src.startswith("seasonal")
    key = MAP_FIELDS[field]["seasonal" if seas else ("ens" if src == "ens" else "det")]
    vals = g[key][i].astype(float)
    if field == "rain" and not seas:   # mm per period -> mm per hour, so 3 h / 6 h / 12 h steps compare
        steps = g["step_h"]
        vals = vals / (steps[i] - steps[i - 1] if i > 0 else np.nan)
    return vals


def map_view(src="ifs", field="temp", i=0, run="latest", vs="none"):
    have = [r for r in runs(src) if _grid_file(src, r).exists()]
    rid, vid = resolve(src, run, vs, have)
    if not rid:
        return {"error": f"No {FEED_LABEL.get(src, src)} map data yet."}
    g = _grid(src, rid)
    seas = src.startswith("seasonal")
    if seas:
        keys = [str(m) for m in g["months"]]
        times = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in keys]
    else:
        keys = list(g["valid_utc"])
        times = [(pd.Timestamp(t, unit="s") + AEST).strftime("%a %d %b %H:%M") for t in keys]
    i = max(0, min(int(i), len(times) - 1))
    vals = _map_values(src, g, field, i)
    note = None
    if vid:   # change map: chosen run minus vs run at the same time / month
        gv = _grid(src, vid)
        vkeys = [str(m) for m in gv["months"]] if seas else list(gv["valid_utc"])
        if keys[i] in vkeys:
            vals = vals - _map_values(src, gv, field, vkeys.index(keys[i]))
        else:
            vals = np.full_like(vals, np.nan)
            note = f"The {run_text(src, vid)} run doesn't cover this time – pick a later time."
    now_i = 0
    if not seas:
        later = np.where(g["valid_utc"] >= datetime.now(timezone.utc).timestamp())[0]
        now_i = int(later[0]) if len(later) else len(times) - 1
    return {"src": src, "field": field, "i": i, "times": times, "run": rid, "run_text": run_text(src, rid),
            "vs": vid, "vs_text": run_text(src, vid), "diff": bool(vid), "note": note, "now_i": now_i,
            "lat": _num(g["lat"], 2), "lon": _num(g["lon"], 2),
            "values": _num(vals.ravel(), 1), "coast": coastline(),
            "cities": [{"city": c, "lat": la, "lon": lo} for _, c, la, lo in C.CITIES],
            "anomaly": seas}
