from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data/catalog/calibration_dataset.csv"


REQUIRED_COLUMNS = [
    "iceberg_id",
    "start_time",
    "end_time",
    "start_latitude",
    "start_longitude",
    "observed_latitude",
    "observed_longitude",
    "observed_u",
    "observed_v",
    "ocean_u",
    "ocean_v",
    "wind_u",
    "wind_v",
]


def main():
    print("=" * 70)
    print("CALIBRATION DATASET QUALITY CONTROL")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    print(f"\nDataset: {INPUT_FILE}")
    print(f"Rows:    {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # ------------------------------------------------------------
    # 1. Required columns
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("1. REQUIRED COLUMNS")
    print("-" * 70)

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        print("FAIL")
        print("Missing columns:", missing_columns)
    else:
        print("PASS - all required columns present")

    # ------------------------------------------------------------
    # 2. Dataset size
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("2. DATASET SIZE")
    print("-" * 70)

    print(f"Rows: {len(df)}")

    if len(df) == 49:
        print("PASS - exactly 49 calibration pairs")
    else:
        print("WARNING - expected 49 rows")

    # ------------------------------------------------------------
    # 3. Iceberg distribution
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("3. ICEBERG DISTRIBUTION")
    print("-" * 70)

    counts = df["iceberg_id"].value_counts().sort_index()

    print(counts.to_string())

    if len(counts) == 7 and (counts == 7).all():
        print("PASS - 7 icebergs × 7 pairs")
    else:
        print("WARNING - unexpected iceberg distribution")

    # ------------------------------------------------------------
    # 4. Time validation
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("4. TIME VALIDATION")
    print("-" * 70)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    duration_hours = (
        df["end_time"] - df["start_time"]
    ).dt.total_seconds() / 3600

    print("Duration statistics:")
    print(duration_hours.describe().to_string())

    invalid_duration = df[duration_hours != 24]

    if invalid_duration.empty:
        print("PASS - every pair is exactly 24 hours")
    else:
        print(
            f"FAIL - {len(invalid_duration)} "
            "pairs are not exactly 24 hours"
        )

    # ------------------------------------------------------------
    # 5. Duplicate pairs
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("5. DUPLICATE CHECK")
    print("-" * 70)

    duplicates = df.duplicated(
        subset=["iceberg_id", "start_time"],
        keep=False
    )

    if not duplicates.any():
        print("PASS - no duplicate iceberg/time pairs")
    else:
        print("FAIL - duplicate pairs found:")
        print(
            df.loc[
                duplicates,
                ["iceberg_id", "start_time", "end_time"]
            ].to_string(index=False)
        )

    # ------------------------------------------------------------
    # 6. Missing values
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("6. MISSING VALUES")
    print("-" * 70)

    numeric_columns = [
        "start_latitude",
        "start_longitude",
        "observed_latitude",
        "observed_longitude",
        "observed_u",
        "observed_v",
        "ocean_u",
        "ocean_v",
        "wind_u",
        "wind_v",
    ]

    missing_counts = df[numeric_columns].isna().sum()

    if missing_counts.sum() == 0:
        print("PASS - no missing numeric values")
    else:
        print("FAIL - missing values found:")
        print(missing_counts[missing_counts > 0])

    # ------------------------------------------------------------
    # 7. Infinite values
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("7. INFINITE VALUE CHECK")
    print("-" * 70)

    numeric_data = df[numeric_columns].to_numpy(dtype=float)

    infinite_count = np.isinf(numeric_data).sum()

    if infinite_count == 0:
        print("PASS - no infinite values")
    else:
        print(f"FAIL - {infinite_count} infinite values found")

    # ------------------------------------------------------------
    # 8. Coordinate validation
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("8. COORDINATE VALIDATION")
    print("-" * 70)

    latitude_columns = [
        "start_latitude",
        "observed_latitude",
    ]

    longitude_columns = [
        "start_longitude",
        "observed_longitude",
    ]

    lat_valid = (
        df[latitude_columns].ge(-90)
        & df[latitude_columns].le(90)
    ).all().all()

    lon_valid = (
        df[longitude_columns].ge(-180)
        & df[longitude_columns].le(180)
    ).all().all()

    if lat_valid and lon_valid:
        print("PASS - coordinates are within valid ranges")
    else:
        print("FAIL - invalid coordinates found")

    # ------------------------------------------------------------
    # 9. Velocity statistics
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("9. VELOCITY STATISTICS")
    print("-" * 70)

    df["observed_speed"] = np.sqrt(
        df["observed_u"] ** 2 +
        df["observed_v"] ** 2
    )

    df["ocean_speed"] = np.sqrt(
        df["ocean_u"] ** 2 +
        df["ocean_v"] ** 2
    )

    df["wind_speed"] = np.sqrt(
        df["wind_u"] ** 2 +
        df["wind_v"] ** 2
    )

    print("\nObserved speed (m/s):")
    print(df["observed_speed"].describe().to_string())

    print("\nOcean speed (m/s):")
    print(df["ocean_speed"].describe().to_string())

    print("\nWind speed (m/s):")
    print(df["wind_speed"].describe().to_string())

    # ------------------------------------------------------------
    # 10. Extremely suspicious values
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("10. EXTREME VALUE CHECK")
    print("-" * 70)

    suspicious_observed = df[df["observed_speed"] > 5]
    suspicious_ocean = df[df["ocean_speed"] > 5]
    suspicious_wind = df[df["wind_speed"] > 60]

    print(
        f"Observed speed > 5 m/s: "
        f"{len(suspicious_observed)}"
    )

    print(
        f"Ocean speed > 5 m/s: "
        f"{len(suspicious_ocean)}"
    )

    print(
        f"Wind speed > 60 m/s: "
        f"{len(suspicious_wind)}"
    )

    if (
        suspicious_observed.empty
        and suspicious_ocean.empty
        and suspicious_wind.empty
    ):
        print("PASS - no obviously extreme values")
    else:
        print(
            "REVIEW - potentially unusual values detected"
        )

    # ------------------------------------------------------------
    # 11. Feature leakage check
    # ------------------------------------------------------------
    print("\n" + "-" * 70)
    print("11. FEATURE LEAKAGE CHECK")
    print("-" * 70)

    forbidden_terms = [
        "anomaly",
        "audit",
        "risk",
        "ground_truth",
        "prediction",
        "label",
    ]

    suspicious_columns = []

    for column in df.columns:
        column_lower = column.lower()

        if any(
            term in column_lower
            for term in forbidden_terms
        ):
            suspicious_columns.append(column)

    if suspicious_columns:
        print("WARNING - suspicious columns:")
        print(suspicious_columns)
    else:
        print(
            "PASS - no obvious audit/anomaly/"
            "prediction columns"
        )

    # ------------------------------------------------------------
    # 12. Final summary
    # ------------------------------------------------------------
    print("\n" + "=" * 70)
    print("QC COMPLETE")
    print("=" * 70)

    print("\nDataset shape:")
    print(df.shape)

    print("\nIcebergs:")
    print(sorted(df["iceberg_id"].unique()))

    print("\nDate range:")
    print(
        df["start_time"].min(),
        "->",
        df["end_time"].max()
    )


if __name__ == "__main__":
    main()