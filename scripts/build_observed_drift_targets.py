import zipfile
from pathlib import Path

import pandas as pd
from pyproj import Geod


# ============================================================
# CONFIG
# ============================================================

BYU_ZIP = Path(
    "data/raw/byu/stats_database_v7.1.zip"
)

REQUESTS = Path(
    "data/catalog/calibration_environment_requests.csv"
)

OUTPUT = Path(
    "data/catalog/observed_drift_targets.csv"
)

HOLDOUT = {"d29c"}

geod = Geod(ellps="WGS84")


# ============================================================
# LOAD REQUESTS
# ============================================================

requests = pd.read_csv(REQUESTS)

requests["date"] = pd.to_datetime(
    requests["date"]
)

requests = requests[
    ~requests["iceberg_id"].isin(HOLDOUT)
].copy()


# ============================================================
# LOAD BYU DATA
# ============================================================

all_targets = []

with zipfile.ZipFile(BYU_ZIP) as z:

    csv_files = {
        Path(name).stem: name
        for name in z.namelist()
        if name.endswith(".csv")
    }

    for iceberg_id in sorted(
        requests["iceberg_id"].unique()
    ):

        if iceberg_id not in csv_files:
            print(
                f"WARNING: {iceberg_id} not found"
            )
            continue

        df = pd.read_csv(
            z.open(csv_files[iceberg_id])
        )

        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%j",
            errors="coerce"
        )

        df = df.dropna(
            subset=["date", "lat", "lon"]
        )

        df = df[
            df["date"].isin(
                requests.loc[
                    requests["iceberg_id"] == iceberg_id,
                    "date"
                ]
            )
        ].copy()

        df = df.sort_values("date")
        df = df.drop_duplicates("date")

        # ----------------------------------------------------
        # Calculate observed 24h velocity
        # ----------------------------------------------------

        for i in range(len(df) - 1):

            p1 = df.iloc[i]
            p2 = df.iloc[i + 1]

            dt_hours = (
                p2["date"] - p1["date"]
            ).total_seconds() / 3600.0

            # Only consecutive ~24h observations
            if not (23 <= dt_hours <= 25):
                continue

            lon1 = float(p1["lon"])
            lat1 = float(p1["lat"])

            lon2 = float(p2["lon"])
            lat2 = float(p2["lat"])

            azimuth, _, distance_m = geod.inv(
                lon1,
                lat1,
                lon2,
                lat2
            )

            distance_km = distance_m / 1000.0

            # Convert azimuth into east/north components.
            # pyproj azimuth:
            # 0° = north
            # 90° = east
            import math

            azimuth_rad = math.radians(azimuth)

            east_mps = (
                distance_m
                * math.sin(azimuth_rad)
                / (dt_hours * 3600.0)
            )

            north_mps = (
                distance_m
                * math.cos(azimuth_rad)
                / (dt_hours * 3600.0)
            )

            all_targets.append({
                "iceberg_id": iceberg_id,

                "start_date":
                    p1["date"].strftime("%Y-%m-%d"),

                "target_date":
                    p2["date"].strftime("%Y-%m-%d"),

                "start_lat":
                    lat1,

                "start_lon":
                    lon1,

                "target_lat":
                    lat2,

                "target_lon":
                    lon2,

                "dt_hours":
                    dt_hours,

                "distance_km":
                    distance_km,

                "observed_u_mps":
                    east_mps,

                "observed_v_mps":
                    north_mps,
            })


# ============================================================
# SAVE
# ============================================================

result = pd.DataFrame(all_targets)

result = result.sort_values(
    ["iceberg_id", "start_date"]
).reset_index(drop=True)

print("\n" + "=" * 80)
print("OBSERVED DRIFT TARGETS")
print("=" * 80)

print(
    result.to_string(index=False)
)

print("\n")
print("Transitions:", len(result))
print(
    "Independent icebergs:",
    result["iceberg_id"].nunique()
)

print(
    "Mean displacement (km):",
    round(result["distance_km"].mean(), 3)
)

print(
    "Median displacement (km):",
    round(result["distance_km"].median(), 3)
)

print(
    "Max displacement (km):",
    round(result["distance_km"].max(), 3)
)

print(
    "Mean observed U (m/s):",
    round(result["observed_u_mps"].mean(), 5)
)

print(
    "Mean observed V (m/s):",
    round(result["observed_v_mps"].mean(), 5)
)


# ============================================================
# SAVE CSV
# ============================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT,
    index=False
)

print("\nSaved:", OUTPUT)