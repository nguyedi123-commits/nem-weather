"""Refresh from the screen (W-018): the Refresh button runs the same downloads as run_download.py, in the background.

Modes: full = BOM + IFS + AIFS + ensemble + seasonal (~18 GB) · light = without the ensemble (~1.5 GB) · bom = BOM only.
One step failing (e.g. no Copernicus key) doesn't stop the others; the screen shows what failed.
Progress: data/progress.json (backend/progress.py), shown in the header and A1.
"""
import logging
import threading

from . import bom, cloud, ecmwf, obs, progress, seasonal, system

log = logging.getLogger("weather.refresh")
MODES = {"cloud": (), "full": ("ifs", "aifs", "ens", "ensx"), "light": ("ifs", "aifs"), "bom": (), "test": ()}
# "test" (not on screen): 2 steps of the newest IFS run (~15 MB) -> *_test2 files, not shown – checks a new install
_thread = None


def running():
    return _thread is not None and _thread.is_alive()


def start(mode):
    """Start a refresh in the background. Returns None if started, else the reason it can't."""
    global _thread
    if mode not in MODES:
        return f"unknown refresh type {mode!r}"
    if running():
        return "A refresh is already running."
    lock = ecmwf.DownloadLock()
    try:
        lock.__enter__()   # another program (e.g. run_download.py) downloading: say so instead of waiting
    except RuntimeError as e:
        return str(e)
    progress.start("Starting refresh", 0)
    _thread = threading.Thread(target=_run, args=(mode, lock), daemon=True, name="refresh")
    _thread.start()
    return None


def _run(mode, lock):
    errors = []
    system.stay_awake(True)
    try:
        steps = [("BOM forecasts", bom.update), ("BOM observations", obs.update)]
        if mode == "cloud":   # W-019: the small NEM-only files the GitHub job made
            steps = [("Cloud", cloud.check)]
        if mode == "test":
            steps = [("ECMWF test", lambda: ecmwf.get_run("ifs", ecmwf.available_runs("ifs", first=True)[0], max_steps=2))]
        if MODES[mode]:
            steps.append(("ECMWF", lambda: ecmwf.update(MODES[mode])))
            steps.append(("Seasonal", seasonal.update))
        for name, fn in steps:
            try:
                progress.start(f"{name}", 0)
                fn()
            except Exception as e:
                log.exception("refresh: %s failed", name)
                errors.append(f"{name}: {str(e)[:150]}")
        progress.finish(error="; ".join(errors) or None)
        log.info("refresh (%s) done%s", mode, f" with problems: {errors}" if errors else "")
    finally:
        system.stay_awake(False)
        lock.__exit__(None, None, None)
