"""Makes the zips in "2. Output" from the built program (copied from NEM Trader's build/make_zip.py):

  Weather.zip           first install: program + clean settings + install note
  Weather (update).zip  update an existing install: program only (keeps its data, history and pages)

  ..\\..\\.venv\\Scripts\\python build\\make_zip.py [built folder, default build\\dist\\Weather]
Nothing from this PC's data folder goes in (the trading PC downloads its own). The built-in pages are inside the
program (web\\layouts); saved pages live in settings\\layouts on the trading PC. No Copernicus key goes in.
"""
import json
import sys
import tempfile
import zipfile
from pathlib import Path

NAME = "Weather"
ROOT = Path(__file__).resolve().parent.parent
dist = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "dist" / NAME
OUT = ROOT.parents[1] / "2. Output"
CLEAN_SETTINGS = {"theme": "light", "page": "Short"}


def make(out, extras):
    tmp = out.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(dist / f"{NAME}.exe", f"{NAME}/{NAME}.exe")
        for f in sorted((dist / "_internal").rglob("*")):
            if f.is_file():
                z.write(f, f"{NAME}/" + f.relative_to(dist).as_posix())
        for src, arc in extras:
            z.write(src, f"{NAME}/{arc}")
    tmp.replace(out)
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        print(f"{out.name}: {len(z.namelist())} files, {out.stat().st_size / 1e6:.0f} MB, check {'OK' if bad is None else bad}")


settings = Path(tempfile.gettempdir()) / "weather_clean_settings.json"
settings.write_text(json.dumps(CLEAN_SETTINGS, indent=1))
OUT.mkdir(exist_ok=True)
make(OUT / f"{NAME}.zip", [(settings, "settings/settings.json"),
                           (ROOT / "build" / "READ ME - install.txt", "READ ME - install.txt")])
make(OUT / f"{NAME} (update).zip", [(ROOT / "build" / "READ ME - update.txt", "READ ME - update.txt")])
