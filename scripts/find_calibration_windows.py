import zipfile
from pathlib import Path

import pandas as pd


ZIP_PATH = Path("data/raw/byu/stats_database_v7.1.zip")

# Current common ERA5 + HYCOM validation domain
MIN_LAT = -67.0
MAX_LAT = -60.0
MIN_LON = -50.0
MAX_LON = -44.0

MIN_CONSECUTIVE_DAYS = 3


def inside_domain(lat, lon):
    return (
        MIN_LAT <= lat <= MAX_LAT
        and MIN_LON <= lon <= MAX_LON
    )


candidates = []

with zipfile.ZipFile(ZIP_PATH) as z:

    for name in z.namelist():

        if not name.endswith(".csv"):
            continue

        iceberg_id = Path(name).stem

        df = pd.read_csv(z.open(name))

        if len(df) < MIN_CONSECUTIVE_DAYS + 1:
            continue

        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%j",
            errors="coerce",
        )

        df = df.dropna(subset=["date", "lat", "lon"])
        df = df.sort_values("date").reset_index(drop=True)

        # Only observations inside environmental domain
        df["inside"] = df.apply(
            lambda r: inside_domain(r["lat"], r["lon"]),
            axis=1
        )

        inside = df[df["inside"]].copy()

        if len(inside) < MIN_CONSECUTIVE_DAYS + 1:
            continue

        # Find consecutive daily sequences
        inside["day_diff"] = inside["date"].diff().dt.days

        group = (inside["day_diff"] != 1).cumsum()

        for _, window in inside.groupby(group):

            if len(window) < MIN_CONSECUTIVE_DAYS + 1:
                continue

            candidates.append({
                "iceberg_id": iceberg_id,
                "start": window["date"].min(),
                "end": window["date"].max(),
                "observations": len(window),
                "pairs": len(window) - 1,
                "lat_min": window["lat"].min(),
                "lat_max": window["lat"].max(),
                "lon_min": window["lon"].min(),
                "lon_max": window["lon"].max(),
            })


result = pd.DataFrame(candidates)

if result.empty:
    print("No calibration windows found.")
    raise SystemExit


result = result.sort_values(
    ["pairs", "observations"],
    ascending=False
)

print("\n" + "=" * 80)
print("BEST HISTORICAL CALIBRATION WINDOWS")
print("=" * 80)

print(
    result.head(50).to_string(index=False)
)

print("\n")
print("Unique icebergs:", result["iceberg_id"].nunique())
print("Candidate windows:", len(result))
print("Total candidate pairs:", result["pairs"].sum())

out = Path(
    "data/catalog/calibration_windows.csv"
)

result.to_csv(out, index=False)

print("\nSaved:", out)