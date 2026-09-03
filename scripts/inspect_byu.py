import zipfile
import pandas as pd
import numpy as np

ZIP_PATH = "data/raw/byu/stats_database_v7.1.zip"

print("===== BYU FIELD INSPECTION =====")

with zipfile.ZipFile(ZIP_PATH) as z:
    csv_files = [
        name for name in z.namelist()
        if name.lower().endswith(".csv")
    ]

    all_lat = []
    all_lon = []
    all_disp = []
    all_size = []
    all_angle = []
    all_gap = []

    for filename in csv_files:
        with z.open(filename) as f:
            df = pd.read_csv(f)

        all_lat.extend(df["lat"].dropna())
        all_lon.extend(df["lon"].dropna())
        all_disp.extend(df["disp"].dropna())
        all_size.extend(df["size"].dropna())
        all_angle.extend(df["vel_angle"].dropna())
        all_gap.extend(df["date_gap"].dropna())

    def stats(name, values):
        values = np.asarray(values, dtype=float)

        print(f"\n{name}")
        print("  count :", len(values))
        print("  min   :", np.min(values))
        print("  max   :", np.max(values))
        print("  mean  :", np.mean(values))
        print("  median:", np.median(values))

    stats("LATITUDE", all_lat)
    stats("LONGITUDE", all_lon)
    stats("DISPLACEMENT (raw)", all_disp)
    stats("SIZE (raw)", all_size)
    stats("VELOCITY ANGLE (raw)", all_angle)
    stats("DATE GAP", all_gap)

    print("\n===== DATE RANGE =====")

    dates = []

    for filename in csv_files:
        with z.open(filename) as f:
            df = pd.read_csv(f)

        dates.extend(df["date"].dropna().astype(str))

    print("Earliest raw date:", min(dates))
    print("Latest raw date  :", max(dates))

    print("\n===== COORDINATE VALIDATION =====")

    invalid_lat = [
        x for x in all_lat
        if x < -90 or x > 90
    ]

    invalid_lon = [
        x for x in all_lon
        if x < -180 or x > 180
    ]

    print("Invalid latitude :", len(invalid_lat))
    print("Invalid longitude:", len(invalid_lon))

    print("\n===== DONE =====")