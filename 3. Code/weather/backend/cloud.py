"""Cloud pick-up (W-019 / W-012): read the list the GitHub job publishes (manifest.json), download only the runs this
PC doesn't have yet (~60 MB each, nothing when nothing is new), unpack them into data/. Runs every hour by itself and
on Refresh → "From the cloud". History stays on this PC as before (cities forever, maps 30 days).
"""
from datetime import datetime, timedelta, timezone
import io
import json
import logging
import os
import re
import threading
import time
import urllib.request
import zipfile

import pandas as pd

from . import config as C, ecmwf, obs, progress

log = logging.getLogger("weather.cloud")
REPO = "nguyedi123-commits/nem-weather"
URL = f"https://github.com/{REPO}/releases/download/data"
EVERY_S = 900   # 15 min: the morning cloud job (~6:56 am Sydney) reaches the screen by ~7:15 (W-024)
SAFE = re.compile(r"^(cities|grid)/[a-z_]+/[0-9a-z_]+\.(parquet|npz)$|^obs/(daily|halfhourly)\.parquet$|^static/lsm\.npz$")
_state_lock = threading.Lock()


def _state_file():
    return C.DATA / "cloud.json"


def load_state():
    try:
        return json.loads(_state_file().read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _save_state(**kw):
    with _state_lock:
        s = {**load_state(), **kw}
        tmp = _state_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(s, indent=1))
        os.replace(tmp, _state_file())


def status():
    s = load_state()
    if s.get("last_check"):
        s["next_check"] = (datetime.fromisoformat(s["last_check"]) + timedelta(seconds=EVERY_S)).isoformat(timespec="seconds")
    return s


def _get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "Weather (NEM screen)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _unpack(blob):
    """Write the zip's files into data/ (only the paths we expect). Returns the obs files for merging."""
    obs_parts = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if not SAFE.match(name):
                log.warning("skipped unexpected file in a cloud zip: %s", name)
                continue
            data = z.read(name)
            if name.startswith("obs/"):
                obs_parts[name] = data
                continue
            dest = C.DATA / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            os.replace(tmp, dest)
    return obs_parts


def _catalog_add(feed, rid, info):
    with ecmwf._catalog_lock:
        cat = ecmwf.load_catalog()
        cat.setdefault(feed, {})[rid] = {"finished": info.get("finished"), "from": "cloud"}
        tmp = ecmwf._catalog_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, indent=1))
        os.replace(tmp, ecmwf._catalog_file())


def check():
    """One pick-up. Returns the number of new files taken in."""
    C.DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        man = json.loads(_get(f"{URL}/manifest.json", 60))
    except Exception as e:
        _save_state(last_check=now, error=f"Cloud not reachable: {e}")
        raise
    cat = ecmwf.load_catalog()
    st = load_state()
    todo = [(feed, rid, info) for feed, rs in man.get("runs", {}).items() for rid, info in sorted(rs.items())
            if rid not in cat.get(feed, {})]
    # oldest first, so a PC that was off a while fills its history in order
    todo.sort(key=lambda x: x[1])
    want_obs = man.get("obs") and man["obs"]["updated"] > st.get("obs_updated", "")
    want_static = man.get("static") and not (C.DATA / "static" / "lsm.npz").exists()
    n = len(todo) + bool(want_obs) + bool(want_static)
    if not n:
        _save_state(last_check=now, error=None, cloud_updated=man.get("updated"), last_job=man.get("last_job"))
        return 0
    progress.start("Cloud (NEM-only files)", n)
    got = 0
    for feed, rid, info in todo:
        blob = _get(f"{URL}/{info['asset']}")
        _unpack(blob)
        _catalog_add(feed, rid, info)
        progress.step(len(blob))
        got += 1
    if want_obs:   # merge into this PC's own history (never replaced)
        blob = _get(f"{URL}/{man['obs']['asset']}")
        for name, data in _unpack(blob).items():
            new = pd.read_parquet(io.BytesIO(data))
            keys = ["region", "date"] if name.endswith("daily.parquet") else ["region", "time_utc"]
            (C.DATA / "obs").mkdir(parents=True, exist_ok=True)
            obs._merge(C.DATA / name, new, keys)
        _save_state(obs_updated=man["obs"]["updated"])
        progress.step(len(blob))
        got += 1
    if want_static:
        blob = _get(f"{URL}/{man['static']['asset']}")
        _unpack(blob)
        progress.step(len(blob))
        got += 1
    ecmwf.prune()
    _save_state(last_check=now, last_new=now, error=None, cloud_updated=man.get("updated"), last_job=man.get("last_job"))
    log.info("cloud: %d new files", got)
    return got


def loop(is_busy):
    """Every 15 minutes (first time shortly after start): pick up new cloud data, unless a refresh is running."""
    time.sleep(15)
    while True:
        if not is_busy():
            lock = ecmwf.DownloadLock()
            try:
                lock.__enter__()
            except RuntimeError:
                lock = None   # another download running: try next hour
            if lock:
                try:
                    if check():
                        progress.finish()
                except Exception as e:
                    log.warning("cloud pick-up failed: %s", e)
                    progress.finish(error=f"Cloud: {e}")
                finally:
                    lock.__exit__(None, None, None)
        time.sleep(EVERY_S)
