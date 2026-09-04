from pathlib import Path

import pandas as pd


INPUT = Path(
    "data/catalog/calibration_windows.csv"
)

OUTPUT = Path(
    "data/catalog/selected_calibration_windows.csv"
)

# Number of independent icebergs to use
MAX_ICEBERGS = 15

# Maximum consecutive days we need from each track
WINDOW_DAYS = 7


df = pd.read_csv(INPUT)

df["start"] = pd.to_datetime(df["start"])
df["end"] = pd.to_datetime(df["end"])

# Prefer long, clean windows
df = df.sort_values(
    ["pairs", "observations"],
    ascending=False
)

selected = []

used_icebergs = set()

for _, row in df.iterrows():

    iceberg = row["iceberg_id"]

    # One calibration window per iceberg
    if iceberg in used_icebergs:
        continue

    if len(used_icebergs) >= MAX_ICEBERGS:
        break

    duration = (row["end"] - row["start"]).days

    if duration < WINDOW_DAYS:
        continue

    # Take first 7 days of the eligible window
    start = row["start"]
    end = start + pd.Timedelta(days=WINDOW_DAYS)

    selected.append({
        "iceberg_id": iceberg,
        "start": start,
        "end": end,
        "pairs": WINDOW_DAYS,
        "lat_min": row["lat_min"],
        "lat_max": row["lat_max"],
        "lon_min": row["lon_min"],
        "lon_max": row["lon_max"],
    })

    used_icebergs.add(iceberg)


result = pd.DataFrame(selected)

print("\n" + "=" * 80)
print("SELECTED CALIBRATION WINDOWS")
print("=" * 80)

print(result.to_string(index=False))

print("\nUnique icebergs:", result["iceberg_id"].nunique())
print("Total windows:", len(result))
print("Approx pairs:", result["pairs"].sum())

result.to_csv(OUTPUT, index=False)

print("\nSaved:", OUTPUT)