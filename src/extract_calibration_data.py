import zipfile
import pandas as pd
from pathlib import Path

ZIP_PATH = Path("data/raw/byu/stats_database_v7.1.zip")
CATALOG_PATH = Path("data/catalog/selected_calibration_windows.csv")
OUTPUT_PATH = Path("data/processed/calibration_data.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

catalog = pd.read_csv(CATALOG_PATH)

rows = []

with zipfile.ZipFile(ZIP_PATH) as z:

    for _, cal in catalog.iterrows():

        iceberg_id = cal["iceberg_id"]
        start = pd.to_datetime(cal["start"])
        end = pd.to_datetime(cal["end"])

        matches = [
            x for x in z.namelist()
            if x.lower().endswith(f"/{iceberg_id.lower()}.csv")
        ]

        if not matches:
            print(f"WARNING: {iceberg_id}.csv not found")
            continue

        file_path = matches[0]

        df = pd.read_csv(z.open(file_path))

        # Convert YYYYDDD → datetime
        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%j"
        )

        # Select calibration window
        window = df[
            (df["date"] >= start) &
            (df["date"] <= end)
        ].copy()

        window["iceberg_id"] = iceberg_id

        rows.append(window)

        print(
            f"{iceberg_id}: "
            f"{len(window)} observations "
            f"({start.date()} → {end.date()})"
        )

result = pd.concat(rows, ignore_index=True)

# Put iceberg_id and date first
cols = ["iceberg_id", "date"] + [
    c for c in result.columns
    if c not in ["iceberg_id", "date"]
]

result = result[cols]

result.to_csv(OUTPUT_PATH, index=False)

print("\n--------------------------------")
print("Final dataset")
print("--------------------------------")
print("Rows:", len(result))
print("Columns:", len(result.columns))
print("Icebergs:", result["iceberg_id"].nunique())
print("\nRows per iceberg:")
print(result.groupby("iceberg_id").size())
print("\nSaved to:", OUTPUT_PATH)