"""Phase 1 test: download one ECMWF IFS run and read values at 5 NEM cities."""
from pathlib import Path
import sys

import pandas as pd
import xarray as xr
from ecmwf.opendata import Client

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "2. Output"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(exist_ok=True)

CITIES = {  # NEM region -> (city, lat, lon)
    "QLD": ("Brisbane", -27.47, 153.03),
    "NSW": ("Sydney", -33.87, 151.21),
    "VIC": ("Melbourne", -37.81, 144.96),
    "SA": ("Adelaide", -34.93, 138.60),
    "TAS": ("Hobart", -42.88, 147.33),
}
PARAMS = ["2t", "2d", "10u", "10v", "100u", "100v", "tcc", "tp", "ssrd"]
STEPS = list(range(0, 75, 3))  # 0-72h, 3-hourly

client = Client(source="ecmwf", model="ifs", resol="0p25")
target = RAW / "ifs_oper_test.grib2"
if not target.exists():
    result = client.retrieve(type="fc", stream="oper", step=STEPS, param=PARAMS, target=str(target))
    print("Run:", result.datetime)
print("File MB:", round(target.stat().st_size / 1e6, 1))

# cfgrib splits fields by level type; open each group and merge
import cfgrib
dsets = cfgrib.open_datasets(str(target), backend_kwargs={"indexpath": ""})

rows = []
for region, (city, lat, lon) in CITIES.items():
    point = {}
    for ds in dsets:
        p = ds.sel(latitude=lat, longitude=lon, method="nearest")
        for var in p.data_vars:
            point[var] = p[var].values
        valid = p["valid_time"].values
    df = pd.DataFrame(point, index=pd.to_datetime(valid))
    df.insert(0, "city", city)
    df.insert(0, "region", region)
    rows.append(df)

df = pd.concat(rows).rename_axis("valid_time_utc").reset_index()
# Friendly units
df["temp_c"] = df.pop("t2m") - 273.15
df["dewpoint_c"] = df.pop("d2m") - 273.15
df["wind10_kmh"] = (df.pop("u10") ** 2 + df.pop("v10") ** 2) ** 0.5 * 3.6
df["wind100_kmh"] = (df.pop("u100") ** 2 + df.pop("v100") ** 2) ** 0.5 * 3.6
df["cloud_pct"] = df.pop("tcc")
df["rain_total_mm"] = df.pop("tp") * 1000          # accumulated since run start
df["solar_total_MJm2"] = df.pop("ssrd") / 1e6      # accumulated since run start
df = df.round(1)
csv = OUT / "phase1_test_ifs_cities.csv"
df.to_csv(csv, index=False)
print(df[df.region == "NSW"].head(10).to_string(index=False))
print("Saved", csv)
