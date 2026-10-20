"""Download ECMWF open-data runs, keep only the east coast, throw the rest away.

How it works
- Each ECMWF file has an index listing where every field sits (byte offsets).
- We download only the fields we need (byte ranges), decode them in memory,
  cut out the east-coast box + the 5 city points, and never save the global data.
- Each finished time step is saved to data/work/<feed>/<run>/ so a run can resume
  after the PC is turned off. When all steps are in, they are combined into
  data/cities/<feed>/<run>.parquet and data/grid/<feed>/<run>.npz, and work is deleted.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import shutil
import threading
import time
import warnings

import eccodes
import numpy as np
import pandas as pd
import requests

from . import config as C, progress

log = logging.getLogger("weather.ecmwf")

STEP_WORKERS = 3    # time steps downloaded at once
RANGE_WORKERS = 4   # connections per time step
BACKFILL_HOURS = {"ifs": 0, "aifs": 0, "ens": 0}   # 0 = newest run only (user, 18 Oct); hours > 0 also fetches missed older runs

_local = threading.local()
_decode_lock = threading.Lock()
_catalog_lock = threading.Lock()
_geo = None


# ---------- HTTP ----------

def _http():
    s = getattr(_local, "s", None)
    if s is None:
        s = _local.s = requests.Session()
    return s


def _get(path, rng=None):
    """GET a file (or byte range) from the first source that has it, with retries."""
    headers = {"Range": f"bytes={rng[0]}-{rng[1] - 1}"} if rng else {}
    err = None
    for attempt in range(4):
        for base in C.SOURCES:
            try:
                r = _http().get(f"{base}/{path}", headers=headers, timeout=90)
                if r.status_code in (200, 206):
                    if rng and len(r.content) != rng[1] - rng[0]:
                        err = IOError(f"short read {path}")
                        continue
                    return r.content
                err = IOError(f"HTTP {r.status_code} {base}/{path}")
            except requests.RequestException as e:
                err = e
        time.sleep(3 * (attempt + 1))
    raise err


def _exists(path):
    for base in C.SOURCES:
        try:
            if _http().head(f"{base}/{path}", timeout=20).status_code == 200:
                return True
        except requests.RequestException:
            pass
    return False


# ---------- Runs ----------

def run_id(run):
    return run.strftime("%Y%m%d%H")


def parse_run(text):
    return datetime.strptime(text, "%Y%m%d%H").replace(tzinfo=timezone.utc)


def _path(feed, run, step, ext):
    f = C.FEEDS[feed]
    d, hh = run.strftime("%Y%m%d"), run.strftime("%H")
    return (f"{d}/{hh}z/{f['model']}/0p25/{f['stream']}/"
            f"{d}{hh}0000-{step}h-{f['stream']}-{f['type']}.{ext}")


def steps_for(feed, run):
    return C.FEEDS[feed]["runs"][run.hour]


def available_runs(feed, now=None, first=False):
    """Runs (newest first) that ECMWF has finished publishing. first=True stops at the newest."""
    now = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    out = []
    for h in range(C.KEEP_DAYS * 24):
        t = now - timedelta(hours=h)
        if t.hour in C.FEEDS[feed]["runs"] and _exists(_path(feed, t, steps_for(feed, t)[-1], "index")):
            out.append(t)
            if first:
                break
    return out


# ---------- Catalog (which runs are finished) ----------

def _catalog_file():
    return C.DATA / "catalog.json"


def load_catalog():
    try:
        return json.loads(_catalog_file().read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _mark_done(feed, run, n_steps):
    with _catalog_lock:
        cat = load_catalog()
        cat.setdefault(feed, {})[run_id(run)] = {
            "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "steps": n_steps}
        tmp = _catalog_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, indent=1))
        os.replace(tmp, _catalog_file())


# ---------- Grid geometry and city points ----------

class Geo:
    """Where the east-coast box and the city points sit inside the global grid."""

    def __init__(self, h, lsm=None):
        g = lambda k: eccodes.codes_get(h, k)
        self.ni, self.nj = g("Ni"), g("Nj")
        lat0, lon0 = g("latitudeOfFirstGridPointInDegrees"), g("longitudeOfFirstGridPointInDegrees")
        dj, di = g("jDirectionIncrementInDegrees"), g("iDirectionIncrementInDegrees")
        sign = 1 if g("jScansPositively") else -1
        lats = lat0 + sign * dj * np.arange(self.nj)
        lons = (lon0 + di * np.arange(self.ni)) % 360
        rows = np.where((lats <= C.GRID["north"]) & (lats >= C.GRID["south"]))[0]
        cols = np.where((lons >= C.GRID["west"]) & (lons <= C.GRID["east"]))[0]
        self.r0, self.r1, self.c0, self.c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
        self.lat, self.lon = lats[self.r0:self.r1], lons[self.c0:self.c1]
        self.city_rc = [self._city_point(*C.CITY_SQUARE.get(city, (lat, lon)), lats, lons, lsm)
                        for _, city, lat, lon in C.CITIES]
        for (_, city, *_), (i, j) in zip(C.CITIES, self.city_rc):
            log.info("%s uses grid point %.2f, %.2f", city, lats[i], lons[j])

    @staticmethod
    def _city_point(lat, lon, lats, lons, lsm):
        """Nearest grid point that is mostly land (so coastal cities don't get sea temperatures)."""
        r = np.argsort(np.abs(lats - lat))[:5]
        c = np.argsort(np.abs(lons - lon % 360))[:5]
        best = None
        for i in r:
            for j in c:
                d = (lats[i] - lat) ** 2 + (lons[j] - lon % 360) ** 2
                land = lsm is None or lsm[i, j] >= C.LAND_MIN
                key = (not land, d)
                if best is None or key < best[0]:
                    best = (key, int(i), int(j))
        return best[1], best[2]

    def cut(self, values):
        v = values.reshape(self.nj, self.ni)
        box = v[self.r0:self.r1, self.c0:self.c1].astype(np.float32)
        pts = np.array([v[i, j] for i, j in self.city_rc], dtype=np.float32)
        return box, pts


def _load_geo():
    """Build grid geometry once, using the land-sea mask from the latest IFS run."""
    global _geo
    if _geo is not None:
        return _geo
    run = available_runs("ifs", first=True)[0]
    idx = _get(_path("ifs", run, 0, "index")).decode()
    items = [json.loads(l) for l in idx.splitlines() if l.strip()]
    lsm_item = next((d for d in items if d["param"] == "lsm"), None)
    first = lsm_item or next(d for d in items if d["param"] == "2t")
    raw = _get(_path("ifs", run, 0, "grib2"), (first["_offset"], first["_offset"] + first["_length"]))
    h = eccodes.codes_new_from_message(raw)
    try:
        lsm = None
        if lsm_item:
            lsm = eccodes.codes_get_values(h).reshape(eccodes.codes_get(h, "Nj"), eccodes.codes_get(h, "Ni"))
        _geo = Geo(h, lsm)
        if lsm is not None:   # east-coast land/sea mask, used to draw the coastline on the Map tab
            (C.DATA / "static").mkdir(parents=True, exist_ok=True)
            np.savez_compressed(C.DATA / "static" / "lsm.npz", lat=_geo.lat, lon=_geo.lon,
                                lsm=lsm[_geo.r0:_geo.r1, _geo.c0:_geo.c1].astype(np.float32))
    finally:
        eccodes.codes_release(h)
    return _geo


# ---------- One time step ----------

def _select(feed, index_text):
    want = set(C.FEEDS[feed]["params"])
    items = [d for d in (json.loads(l) for l in index_text.splitlines() if l.strip())
             if d.get("levtype") == "sfc" and d["param"] in want]
    items.sort(key=lambda d: d["_offset"])
    blocks = []   # touching fields merged into one request
    for d in items:
        a, b = d["_offset"], d["_offset"] + d["_length"]
        if blocks and a <= blocks[-1][1]:
            blocks[-1][1] = max(b, blocks[-1][1])
            blocks[-1][2].append(d)
        else:
            blocks.append([a, b, [d]])
    return items, blocks


def _do_step(feed, run, step, work, geo):
    out = work / f"s{step:03d}.npz"
    if out.exists():
        return 0
    t0 = time.time()
    items, blocks = _select(feed, _get(_path(feed, run, step, "index")).decode())
    expected = len([p for p in C.FEEDS[feed]["params"] if p not in C.MAXMIN])
    if feed in ("ens", "ensx"):
        expected *= 50
    got = len([d for d in items if d["param"] not in C.MAXMIN])
    if expected == 0:   # max/min-only feed (ensx): 50 members x max + min
        expected, got = 100, len(items)
    if got < expected:
        raise IOError(f"{feed} {run_id(run)} step {step}: {len(items)} fields, expected {expected}")

    grib = _path(feed, run, step, "grib2")
    box, pts, units = {}, {}, {}   # param -> {member: array}

    def fetch(block):
        a, b, ds = block
        data = _get(grib, (a, b))
        with _decode_lock:
            for d in ds:
                h = eccodes.codes_new_from_message(data[d["_offset"] - a: d["_offset"] - a + d["_length"]])
                try:
                    g, p = geo.cut(eccodes.codes_get_values(h))
                    units[C.MAXMIN.get(d["param"], d["param"])] = eccodes.codes_get(h, "units")
                finally:
                    eccodes.codes_release(h)
                m = int(d.get("number", 0) or 0)
                prm = C.MAXMIN.get(d["param"], d["param"])
                box.setdefault(prm, {})[m] = g
                pts.setdefault(prm, {})[m] = p
        return b - a

    with ThreadPoolExecutor(RANGE_WORKERS) as ex:
        nbytes = sum(ex.map(fetch, blocks))

    arrays = {}
    for prm in box:
        members = sorted(box[prm])
        g = np.stack([box[prm][m] for m in members])      # (member, lat, lon)
        p = np.stack([pts[prm][m] for m in members])      # (member, city)
        arrays[f"g_{prm}"], arrays[f"c_{prm}"] = g, p
        arrays["members"] = np.array(members)
        arrays[f"u_{prm}"] = np.array(units[prm])
    if feed == "ens":   # save space: wind speed instead of u/v for the map
        arrays["g_ws100"] = np.hypot(arrays.pop("g_100u"), arrays.pop("g_100v"))
    tmp = out.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        np.savez(f, **arrays)
    os.replace(tmp, out)
    log.info("%s %s step %3dh  %4.0f MB  %4.1fs", feed, run_id(run), step, nbytes / 1e6, time.time() - t0)
    progress.step(nbytes)
    return nbytes


# ---------- Combine steps into final files ----------

def _scale(files, prm):
    """Multiplier to trader units, based on the unit written in the file."""
    unit = str(files[0][f"u_{prm}"]) if f"u_{prm}" in files[0].files else ""
    if prm == "tp":
        return {"m": 1000.0, "kg m**-2": 1.0, "mm": 1.0}[unit]
    if prm == "tcc":
        return {"(0 - 1)": 100.0, "%": 1.0}[unit]
    return 1.0


def _per_period(acc, hours):
    """Totals-since-start -> amount in each period. First step has no period (NaN)."""
    out = np.full_like(acc, np.nan, dtype=np.float32)
    out[1:] = np.diff(acc, axis=0)
    out[1:] = np.maximum(out[1:], 0)
    return out


def _stack(files, key):
    """Stack one field over all steps; steps without it (max/min at 0 h) become NaN."""
    shape = next(f[key].shape for f in files if key in f.files)
    return np.stack([f[key] if key in f.files else np.full(shape, np.nan, np.float32) for f in files])


def _wind_dir(u, v):
    return (270 - np.degrees(np.arctan2(v, u))) % 360


def _derive(get, hours, has, sc):
    """Raw ECMWF fields -> trader units. `get(param)` returns stacked arrays (step first)."""
    dt = np.diff(hours, prepend=np.nan).astype(np.float32)
    shape = (-1,) + (1,) * (get("2t").ndim - 1)
    dt = dt.reshape(shape)
    f = {"temp_c": get("2t") - 273.15}
    if "mx2t" in has:
        f["tmax_c"] = get("mx2t") - 273.15
        f["tmin_c"] = get("mn2t") - 273.15
        if hours[0] == 0:   # no max/min window at 0 h (ECMWF sends zeros)
            f["tmax_c"][0] = np.nan
            f["tmin_c"][0] = np.nan
    if "2d" in has:
        f["dewpoint_c"] = get("2d") - 273.15
    if "10u" in has:
        f["wind10_kmh"] = np.hypot(get("10u"), get("10v")) * 3.6
    f["wind100_kmh"] = (np.hypot(get("100u"), get("100v")) if "100u" in has else get("ws100")) * 3.6
    if "tcc" in has:
        f["cloud_pct"] = get("tcc") * sc("tcc")
    f["rain_mm"] = _per_period(get("tp") * sc("tp"), hours)
    f["solar_wm2"] = _per_period(get("ssrd"), hours) / (dt * 3600)
    return f


def _finish_maxmin(feed, run, steps, work, tag=""):
    """ensx (W-022): only max / min temperature per member and city – no map. Merged into the ensemble by views."""
    rows = []
    for s in steps:
        f = np.load(work / f"s{s:03d}.npz")
        members = f["members"]
        hi, lo = f["c_mx2t"] - 273.15, f["c_mn2t"] - 273.15        # (member, city)
        for mi, m in enumerate(members):
            for ci, (region, city, *_) in enumerate(C.CITIES):
                rows.append((s, int(m), region, city, float(hi[mi, ci]), float(lo[mi, ci])))
        f.close()
    df = pd.DataFrame(rows, columns=["step_h", "member", "region", "city", "tmax_c", "tmin_c"])
    df.insert(0, "run_utc", run.replace(tzinfo=None))
    df.insert(1, "valid_utc", df["run_utc"] + pd.to_timedelta(df["step_h"], unit="h"))
    out = C.DATA / "cities" / feed
    out.mkdir(parents=True, exist_ok=True)
    df.round({"tmax_c": 2, "tmin_c": 2}).to_parquet(out / f"{run_id(run)}{tag}.parquet", index=False)
    shutil.rmtree(work, ignore_errors=True)
    if not tag:
        _mark_done(feed, run, len(steps))


def _finish(feed, run, steps, work, geo, tag=""):
    """tag = "_testN" for test runs: own file names, not added to the catalog."""
    if feed == "ensx":
        return _finish_maxmin(feed, run, steps, work, tag)
    files = [np.load(work / f"s{s:03d}.npz") for s in steps]
    has = {k[2:] for f in files for k in f.files if k.startswith(("g_", "c_"))}
    hours = np.array(steps, dtype=np.float32)
    valid = pd.to_datetime([run.replace(tzinfo=None) + timedelta(hours=s) for s in steps])
    members = files[0]["members"]
    ens = feed == "ens"

    # Cities: table with one row per time (and member for the ensemble)
    cget = lambda p: _stack(files, f"c_{p}")                          # (step, member, city)
    sc = lambda p: _scale(files, p)
    cf = _derive(cget, hours, has, sc)
    if "10u" in has:
        cf["wind10_dir"] = _wind_dir(cget("10u"), cget("10v"))
    cf["wind100_dir"] = _wind_dir(cget("100u"), cget("100v"))
    n_s, n_m, n_c = cf["temp_c"].shape
    idx = pd.MultiIndex.from_product([range(n_s), range(n_m), range(n_c)], names=["s", "m", "c"])
    df = pd.DataFrame({k: v.reshape(-1).astype(np.float32) for k, v in cf.items()}, index=idx).reset_index()
    df.insert(0, "run_utc", run.replace(tzinfo=None))
    s = df.pop("s").to_numpy()
    df.insert(1, "valid_utc", valid[s])
    df.insert(2, "step_h", np.array(steps)[s])
    df.insert(3, "region", [C.CITIES[i][0] for i in df["c"]])
    df.insert(4, "city", [C.CITIES[i][1] for i in df.pop("c")])
    member = members[df.pop("m").to_numpy()]
    if ens:
        df.insert(5, "member", member)
    df = df.round({k: 2 for k in cf})
    cdir = C.DATA / "cities" / feed
    cdir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cdir / f"{run_id(run)}{tag}.parquet", index=False)

    # Map grid: one field at a time to keep memory low
    gdir = C.DATA / "grid" / feed
    gdir.mkdir(parents=True, exist_ok=True)
    grid = {"lat": geo.lat.astype(np.float32), "lon": geo.lon.astype(np.float32),
            "valid_utc": valid.values.astype("datetime64[s]").astype(np.int64), "step_h": np.array(steps)}
    cache = {}

    def gget(p):
        if p not in cache:
            cache[p] = _stack(files, f"g_{p}")                          # (step, member, lat, lon)
        return cache[p]

    keys = ["temp_c", "wind100_kmh", "rain_mm", "solar_wm2"] if ens else \
        ["temp_c", "dewpoint_c", "wind10_kmh", "wind100_kmh", "cloud_pct", "rain_mm", "solar_wm2"]
    if "mx2t" in has:
        keys[1:1] = ["tmax_c", "tmin_c"]
    warnings.filterwarnings("ignore", "All-NaN slice", RuntimeWarning)
    warnings.filterwarnings("ignore", "Mean of empty slice", RuntimeWarning)
    for k in keys:
        one = _derive_one(k, gget, hours, has, sc)
        if ens:
            q = np.nanpercentile(one, [10, 50, 90], axis=1)
            for name, arr in (("p10", q[0]), ("p50", q[1]), ("p90", q[2]), ("mean", np.nanmean(one, axis=1))):
                grid[f"{k}_{name}"] = arr.astype(np.float16)
        else:
            grid[k] = one[:, 0].astype(np.float16)
        cache.clear()
    tmp = gdir / f"{run_id(run)}{tag}.tmp"
    with open(tmp, "wb") as f:
        np.savez_compressed(f, **grid)
    os.replace(tmp, gdir / f"{run_id(run)}{tag}.npz")
    for f in files:
        f.close()
    shutil.rmtree(work, ignore_errors=True)
    if not tag:
        _mark_done(feed, run, len(steps))


def _derive_one(key, get, hours, has, sc):
    dt = np.diff(hours, prepend=np.nan).astype(np.float32).reshape(-1, 1, 1, 1)
    if key == "temp_c":
        return get("2t") - 273.15
    if key in ("tmax_c", "tmin_c"):
        v = get("mx2t" if key == "tmax_c" else "mn2t") - 273.15
        if hours[0] == 0:   # no max/min window at 0 h (ECMWF sends zeros)
            v[0] = np.nan
        return v
    if key == "dewpoint_c":
        return get("2d") - 273.15
    if key == "wind10_kmh":
        return np.hypot(get("10u"), get("10v")) * 3.6
    if key == "wind100_kmh":
        return (get("ws100") if "ws100" in has else np.hypot(get("100u"), get("100v"))) * 3.6
    if key == "cloud_pct":
        return get("tcc") * sc("tcc")
    if key == "rain_mm":
        return _per_period(get("tp") * sc("tp"), hours)
    if key == "solar_wm2":
        return _per_period(get("ssrd"), hours) / (dt * 3600)
    raise KeyError(key)


# ---------- Public ----------

class DownloadLock:
    """Only one downloader at a time (app + scheduled task). Released automatically if the process dies."""

    def __enter__(self):
        C.DATA.mkdir(parents=True, exist_ok=True)
        self.f = open(C.DATA / "download.lock", "a+")
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.f.close()
            raise RuntimeError("Another download is already running")
        return self

    def __exit__(self, *exc):
        if os.name == "nt":
            import msvcrt
            self.f.seek(0)
            msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        self.f.close()


def get_run(feed, run, max_steps=None, part=""):
    """Download one run (resumes if partly done). Returns True when finished."""
    steps = steps_for(feed, run)[:max_steps] if max_steps else steps_for(feed, run)
    rid = run_id(run)
    work = C.DATA / "work" / feed / (rid + (f"_test{max_steps}" if max_steps else ""))
    work.mkdir(parents=True, exist_ok=True)
    geo = _load_geo()
    t0 = time.time()
    already = sum((work / f"s{s:03d}.npz").exists() for s in steps)
    log.info("%s %s: %d steps (%d already done)", feed, rid, len(steps), already)
    progress.start(C.FEEDS[feed]["label"], len(steps), part, rid, already)
    with ThreadPoolExecutor(STEP_WORKERS) as ex:
        nbytes = sum(ex.map(lambda s: _do_step(feed, run, s, work, geo), steps))
    _finish(feed, run, steps, work, geo, f"_test{max_steps}" if max_steps else "")
    log.info("%s %s done: %.0f MB in %.0f s", feed, rid, nbytes / 1e6, time.time() - t0)
    return True


def update(feeds=None):
    """Catch up: fetch missing runs, newest first. Safe to call any time."""
    cat = load_catalog()
    now = datetime.now(timezone.utc)
    todo = []   # (feed, run) – listed first so the screen can say "part 2 of 3"
    for feed in feeds or C.FEEDS:
        runs = available_runs(feed, now)
        if not runs:
            continue
        keep = [r for r in runs if now - r <= timedelta(hours=BACKFILL_HOURS[feed] + 12)] or runs[:1]
        if BACKFILL_HOURS[feed] == 0:
            keep = runs[:1]
        todo += [(feed, run) for run in keep if run_id(run) not in cat.get(feed, {})]
    for i, (feed, run) in enumerate(todo, 1):
        get_run(feed, run, part=f"{i} of {len(todo)}")
    prune()
    return len(todo)


def prune():
    """Delete map data older than GRID_KEEP_DAYS (city tables are kept)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=C.GRID_KEEP_DAYS)
    for f in (C.DATA / "grid").glob("*/*.npz"):
        try:
            if parse_run(f.stem[:10]) < cutoff:
                f.unlink()
        except ValueError:
            pass
