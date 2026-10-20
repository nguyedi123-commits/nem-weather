"""Weather – ECMWF + BOM forecasts for the NEM east coast. One window on one screen.

  python weather.py                  the program window (what Weather.exe does)
  python weather.py --browser        server only (dev copy): open http://127.0.0.1:8892 in the browser

Shows what is in data\\. New data: every hour from the cloud (W-019, small NEM-only files made by the GitHub job),
or the Refresh button (cloud, or directly from ECMWF as a back-up).
"""
import argparse
import logging
import sys
import threading
import time

from backend import cloud, config as C, refresh, server, system


def main():
    ap = argparse.ArgumentParser(description="Weather")
    ap.add_argument("--port", type=int, default=8892)
    ap.add_argument("--browser", action="store_true", help="server only, no window")
    a = ap.parse_args()

    C.DATA.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(C.DATA / "weather.log", encoding="utf-8")]
    if not system.FROZEN:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
                        handlers=handlers)
    log = logging.getLogger("weather")

    if not a.browser and not system.single_instance():
        system.message("Weather is already running.")
        return 0
    srv = server.start(a.port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    log.info("Weather running at %s (data: %s)", url, C.DATA)
    print(f"Weather screen: {url}  (Ctrl+C to stop)", flush=True)
    # W-019 / W-012: new NEM-only data from the cloud every hour (tiny when nothing is new)
    threading.Thread(target=cloud.loop, args=(refresh.running,), daemon=True, name="cloud").start()

    if a.browser:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0

    n = system.unblock_program_files()
    if n:
        log.info("removed the 'from the internet' mark from %d program files", n)
    try:
        import webview   # only needed for the window
        webview.create_window("Weather", url, width=1600, height=950, maximized=True, min_size=(900, 600))
        webview.start(private_mode=False, storage_path=str(C.DATA / "webview"))
    except Exception:
        log.exception("built-in window failed: opening the screen in Microsoft Edge instead")
        if not system.open_in_edge(url, C.DATA / "edge"):
            system.message(f"Weather could not open its window.\n\nOpen this address in a browser instead:\n{url}"
                           f"\n\nDetails: {C.DATA / 'weather.log'}")
            while True:
                time.sleep(3600)
    log.info("window closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
