"""Command line for the ECMWF downloader.

  python run_download.py --update                     catch up all feeds
  python run_download.py --feed ifs                   latest IFS run
  python run_download.py --feed ens --max-steps 2     quick test (first 2 steps)
  python run_download.py --seasonal                   newest seasonal outlooks only (ECMWF + BOM, Copernicus)
  python run_download.py --bom                        BOM city forecasts + observations only
"""
import argparse
import logging

from backend import bom, config as C, ecmwf, obs, progress, seasonal

ap = argparse.ArgumentParser()
ap.add_argument("--feed", choices=list(C.FEEDS))
ap.add_argument("--run", default="latest", help="latest or YYYYMMDDHH")
ap.add_argument("--max-steps", type=int)
ap.add_argument("--update", action="store_true")
ap.add_argument("--seasonal", action="store_true")
ap.add_argument("--bom", action="store_true")
a = ap.parse_args()

C.DATA.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
                    handlers=[logging.StreamHandler(), logging.FileHandler(C.DATA / "download.log")])

def run():
    if a.seasonal:
        seasonal.update()
    elif a.bom:
        bom.update()
        obs.update()
    elif a.update:
        bom.update()
        obs.update()
        ecmwf.update()
        seasonal.update()
    else:
        when = ecmwf.available_runs(a.feed, first=True)[0] if a.run == "latest" else ecmwf.parse_run(a.run)
        ecmwf.get_run(a.feed, when, a.max_steps)


with ecmwf.DownloadLock():
    progress.start("Starting refresh", 0)
    try:
        run()
        progress.finish()
    except BaseException as e:   # incl. Ctrl+C: the screen shows the refresh stopped
        progress.finish(error=f"{type(e).__name__}: {e}")
        raise
