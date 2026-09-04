import zipfile
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

WINDOWS_PATH = Path(
    "data/catalog/selected_calibration_windows.csv"
)

BYU_ZIP_PATH = Path(
    "data/raw/byu/stats_database_v7.1.zip"
)

OUTPUT_PATH = Path(
    "data/catalog/calibration_environment_requests.csv"
)

# d29c is reserved as the final holdout validation track.
HOLDOUT_ICEBERGS = {"d29c"}


# ============================================================
# LOAD SELECTED WINDOWS
# ============================================================

windows = pd.read_csv(WINDOWS_PATH)

windows["start"] = pd.to_datetime(windows["start"])
windows["end"] = pd.to_datetime(windows["end"])

# Remove holdout iceberg(s)
windows = windows[
    ~windows["iceberg_id"].isin(HOLDOUT_ICEBERGS)
].copy()


# ============================================================
# EXTRACT EXACT BYU OBSERVATIONS
# ============================================================

rows = []

with zipfile.ZipFile(BYU_ZIP_PATH) as z:

    csv_files = {
        Path(name).stem: name
        for name in z.namelist()
        if name.endswith(".csv")
    }

    for _, window in windows.iterrows():

        iceberg_id = window["iceberg_id"]

        if iceberg_id not in csv_files:
            print(f"WARNING: Missing BYU file for {iceberg_id}")
            continue

        df = pd.read_csv(
            z.open(csv_files[iceberg_id])
        )

        # BYU date format: YYYY + Julian day
        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%j",
            errors="coerce"
        )

        df = df.dropna(
            subset=["date", "lat", "lon"]
        )

        # Exact selected window
        df = df[
            (df["date"] >= window["start"]) &
            (df["date"] <= window["end"])
        ].copy()

        df = df.sort_values("date")

        # ----------------------------------------------------
        # Store exact observation
        # ----------------------------------------------------

        for _, row in df.iterrows():

            rows.append({
                "iceberg_id": iceberg_id,
                "date": row["date"].strftime("%Y-%m-%d"),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
            })


# ============================================================
# BUILD RESULT
# ============================================================

result = pd.DataFrame(rows)

if result.empty:
    raise RuntimeError(
        "No BYU observations found for selected calibration windows."
    )


result = result.sort_values(
    ["iceberg_id", "date"]
).reset_index(drop=True)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 80)
print("CALIBRATION ENVIRONMENT REQUESTS")
print("=" * 80)

print()

print(result.to_string(index=False))

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    f"Rows              : {len(result)}"
)

print(
    f"Icebergs          : {result['iceberg_id'].nunique()}"
)

print(
    f"Unique dates      : {result['date'].nunique()}"
)

print(
    f"Holdout excluded  : {', '.join(sorted(HOLDOUT_ICEBERGS))}"
)


# ============================================================
# CHECK DAILY CONTINUITY
# ============================================================

print()
print("=" * 80)
print("DAILY CONTINUITY CHECK")
print("=" * 80)

continuity_rows = []

for iceberg_id, group in result.groupby("iceberg_id"):

    dates = pd.to_datetime(
        group["date"]
    ).sort_values()

    daily_pairs = (
        dates.diff().dt.days == 1
    ).sum()

    continuity_rows.append({
        "iceberg_id": iceberg_id,
        "observations": len(dates),
        "daily_pairs": int(daily_pairs),
        "start": dates.min().strftime("%Y-%m-%d"),
        "end": dates.max().strftime("%Y-%m-%d"),
    })


continuity = pd.DataFrame(
    continuity_rows
).sort_values("iceberg_id")

print(
    continuity.to_string(index=False)
)

print()
print(
    "Total daily pairs:",
    continuity["daily_pairs"].sum()
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_PATH,
    index=False
)

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)

print(
    f"Saved: {OUTPUT_PATH}"
)