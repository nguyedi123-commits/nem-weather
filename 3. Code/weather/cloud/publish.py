"""Cloud refresh (W-019), run by the GitHub job (.github/workflows/refresh.yml).

Downloads with the same code as run_download.py (only the NEM east coast is kept), then publishes each NEW run as a
small zip on the GitHub release "data", plus manifest.json = the list of what is there. Weather.exe reads that list
every 15 minutes and fetches only what it doesn't have (backend/cloud.py). Cloud copies are deleted after 30 days
(seasonal after 400) – each trading PC keeps its own history.

  python cloud/publish.py --mode full|light|bom      needs GH_TOKEN + GITHUB_REPOSITORY (set by GitHub) and the gh tool
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import bom, config as C, ecmwf, obs, seasonal   # noqa: E402

TAG = "data"
KEEP_DAYS = {"seasonal": 400, "seasonal_bom": 400, "seasonal_cfs": 400}   # others: 30
MODES = {"full": ("ifs", "aifs", "ens", "ensx"), "light": ("ifs", "aifs"), "bom": ()}
REPO = os.environ.get("GITHUB_REPOSITORY", "nguyedi123-commits/nem-weather")
URL = f"https://github.com/{REPO}/releases/download/{TAG}"
OUT = C.DATA / "publish"
log = logging.getLogger("weather.publish")


def gh(*args, check=True):
    r = subprocess.run(["gh", *args, "--repo", REPO], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {r.stderr.strip()[:300]}")
    return r


def get_manifest():
    try:
        with urllib.request.urlopen(f"{URL}/manifest.json", timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        log.info("no manifest yet (%s) – starting a new one", e)
        return {"runs": {}}


def run_time(feed, rid):
    if feed.startswith("seasonal"):
        return datetime.strptime(rid, "%Y%m").replace(tzinfo=timezone.utc)
    if feed == "bom":
        return datetime.strptime(rid, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    return ecmwf.parse_run(rid)


def files_for(feed, rid):
    fs = [C.DATA / "cities" / feed / f"{rid}.parquet", C.DATA / "grid" / feed / f"{rid}.npz"]
    return [f for f in fs if f.exists()]


def pack(name, files):
    """Zip with paths relative to data/ (cities/…, grid/…, obs/…, static/…)."""
    OUT.mkdir(parents=True, exist_ok=True)
    z = OUT / name
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(C.DATA).as_posix())
    return z


def publish(man, now, mode, errors, new):
    """Upload what is new since the last call, then the manifest (last). Called after each slow step.
    new = run files published so far in this job (filled in here)."""
    runs = man["runs"]
    uploads = []
    for feed, rs in ecmwf.load_catalog().items():
        if feed == "obs" or not isinstance(rs, dict):
            continue
        for rid, info in rs.items():
            if rid in runs.get(feed, {}) or not files_for(feed, rid):
                continue
            z = pack(f"{feed}__{rid}.zip", files_for(feed, rid))
            uploads.append(z)
            runs.setdefault(feed, {})[rid] = {"asset": z.name, "size": z.stat().st_size,
                                              "finished": info.get("finished") or now.isoformat(timespec="seconds")}
    obs_files = [f for f in (C.DATA / "obs" / "daily.parquet", C.DATA / "obs" / "halfhourly.parquet") if f.exists()]
    if obs_files and man.get("obs", {}).get("updated") != now.isoformat(timespec="seconds"):
        uploads.append(pack("obs.zip", obs_files))
        man["obs"] = {"asset": "obs.zip", "updated": now.isoformat(timespec="seconds")}
    lsm = C.DATA / "static" / "lsm.npz"
    if lsm.exists() and "static" not in man:
        uploads.append(pack("static.zip", [lsm]))
        man["static"] = {"asset": "static.zip"}

    # delete cloud copies past their time
    old = []
    for feed, rs in runs.items():
        keep = timedelta(days=KEEP_DAYS.get(feed, 30))
        for rid in [r for r in rs if now - run_time(feed, r) > keep]:
            old.append(rs.pop(rid)["asset"])
    for name in old:
        gh("release", "delete-asset", TAG, name, "-y", check=False)

    new += [z.name for z in uploads if z.name not in ("obs.zip", "static.zip")]
    man["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    man["last_job"] = {"time": now.isoformat(timespec="seconds"), "mode": mode, "errors": list(errors), "new": list(new)}
    mf = OUT / "manifest.json"
    OUT.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps(man, indent=1))
    for k in range(0, len(uploads), 10):   # files first, the list last: Weather.exe never sees a run before its file
        gh("release", "upload", TAG, *[str(z) for z in uploads[k:k + 10]], "--clobber")
    gh("release", "upload", TAG, str(mf), "--clobber")
    log.info("published %d files, removed %d old; problems: %s", len(uploads), len(old), errors or "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODES), default="light")
    a = ap.parse_args()
    C.DATA.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")
    now = datetime.now(timezone.utc)

    if gh("release", "view", TAG, check=False).returncode:
        gh("release", "create", TAG, "--title", "Weather data – NEM east coast",
           "--notes", "Small NEM-only forecast files made by the cloud job (W-019). Weather.exe downloads them; "
                      "see manifest.json. Data: ECMWF (CC BY 4.0), BOM, Copernicus.", "--latest=false")
    man = get_manifest()
    runs = man.setdefault("runs", {})

    # tell the downloader what is already published, so it fetches only new runs
    cat = {feed: {rid: {"finished": info.get("finished")} for rid, info in rs.items()} for feed, rs in runs.items()}
    (C.DATA / "catalog.json").write_text(json.dumps(cat))

    errors, new = [], []

    def run(name, fn):
        try:
            fn()
        except Exception as e:
            log.exception("%s failed", name)
            errors.append(f"{name}: {str(e)[:200]}")

    run("BOM forecasts", bom.update)
    run("BOM observations", obs.update)
    if MODES[a.mode]:
        run("ECMWF", lambda: ecmwf.update(MODES[a.mode]))
    publish(man, now, a.mode, errors, new)   # forecasts out first: the Copernicus queue below can take hours
    if a.mode == "full":   # monthly – kept out of the morning jobs
        run("Seasonal", seasonal.update)
        publish(man, now, a.mode, errors, new)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
