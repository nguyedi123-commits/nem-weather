# PyInstaller recipe for Weather (one-folder build: faster start, fewer antivirus false alarms).
# Copied from NEM Trader's build/trading_screen.spec. Run build\build.bat rather than this directly.
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "web"), "web")]
binaries = []
hiddenimports = ["clr", "pandas", "pyarrow", "winreg"] + collect_submodules("ecmwf.datastores")
# window (pywebview + .NET), the ECMWF file reader (eccodes: DLLs + its cffi bindings), Copernicus client
for pkg in ("webview", "clr_loader", "pythonnet", "eccodes", "gribapi", "findlibs", "cdsapi", "multiurl"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(ROOT, "weather.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "playwright", "xarray", "cfgrib", "scipy", "dask"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Weather",
    icon=os.path.join(SPECPATH, "icon.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="Weather")
