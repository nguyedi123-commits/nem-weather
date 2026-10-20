"""Download progress for the screen (W-016): the downloader writes data/progress.json, the screen reads it.

{"active": true, "label": "IFS ensemble (50 runs)", "part": "2 of 3", "run": "2026101900", "done": 12, "total": 45,
 "bytes": 4.1e9, "started": "...", "updated": "...", "error": null}
"""
from datetime import datetime, timezone
import json
import os
import threading

from . import config as C

STALE_MIN = 10   # no update for this long while "active" = the download stopped (PC off, killed)
_lock = threading.Lock()
_state = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write():
    _state["updated"] = _now()
    f = C.DATA / "progress.json"
    tmp = f.with_suffix(".ptmp")
    tmp.write_text(json.dumps(_state))
    os.replace(tmp, f)


def start(label, total, part="", run="", done=0):
    with _lock:
        started = _state.get("started") if _state.get("active") else None
        _state.clear()
        _state.update(active=True, label=label, part=part, run=run, done=done, total=total, bytes=0,
                      started=started or _now(), error=None)
        _write()


def step(nbytes=0):
    with _lock:
        if _state:
            _state["done"] = _state.get("done", 0) + 1
            _state["bytes"] = _state.get("bytes", 0) + nbytes
            _write()


def finish(error=None):
    with _lock:
        _state.update(active=False, finished=_now(), error=error)
        _write()


def read():
    try:
        p = json.loads((C.DATA / "progress.json").read_text())
    except (FileNotFoundError, ValueError):
        return {"active": False}
    if p.get("active"):
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(p["updated"])).total_seconds() / 60
        p["stalled"] = age > STALE_MIN
    return p
