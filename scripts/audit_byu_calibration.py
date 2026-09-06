from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


CALIBRATION_FILE = ROOT / "data" / "catalog" / "calibration_observations.csv"
WINDOW_FILE = ROOT / "data" / "catalog" / "selected_calibration_windows.csv"


def main():
    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(
            f"Calibration observations not found: {CALIBRATION_FILE}"
        )

    if not WINDOW_FILE.exists():
        raise FileNotFoundError(
            f"Selected calibration windows not found: {WINDOW_FILE}"
        )

    df = pd.read_csv(CALIBRATION_FILE)
    windows = pd.read_csv(WINDOW_FILE)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    print("=" * 70)
    print("BYU CALIBRATION OBSERVATION AUDIT")
    print("=" * 70)

    print(f"\nCalibration file: {CALIBRATION_FILE}")
    print(f"Selected windows: {WINDOW_FILE}")

    print("\n--- BASIC DATASET ---")
    print(f"Total pairs:        {len(df)}")
    print(f"Unique icebergs:    {df['iceberg_id'].nunique()}")
    print(
        f"Date range:         "
        f"{df['start_time'].min().date()} -> {df['end_time'].max().date()}"
    )

    expected_icebergs = windows["iceberg_id"].astype(str).tolist()

    print("\n--- PAIRS PER ICEBERG ---")

    counts = df.groupby("iceberg_id").size()

    all_counts_correct = True

    for iceberg_id in expected_icebergs:
        count = int(counts.get(iceberg_id, 0))
        status = "OK" if count == 7 else "CHECK"

        if count != 7:
            all_counts_correct = False

        print(f"{iceberg_id:8s} {count:2d}/7  {status}")

    unexpected = sorted(set(df["iceberg_id"]) - set(expected_icebergs))

    if unexpected:
        all_counts_correct = False
        print("\nUnexpected icebergs found:")
        for iceberg_id in unexpected:
            print(f"  {iceberg_id}")

    print("\n--- DURATION CHECK ---")

    duration_hours = (
        df["end_time"] - df["start_time"]
    ).dt.total_seconds() / 3600.0

    duration_ok = np.isclose(duration_hours, 24.0)

    print(f"24-hour pairs:      {duration_ok.sum()}/{len(df)}")
    print(f"Non-24-hour pairs:  {(~duration_ok).sum()}")

    if (~duration_ok).any():
        print("\nNon-24-hour pairs:")
        cols = ["iceberg_id", "start_time", "end_time"]
        temp = df.loc[~duration_ok, cols].copy()
        temp["duration_hours"] = duration_hours[~duration_ok].values
        print(temp.to_string(index=False))

    print("\n--- MISSING VALUE CHECK ---")

    important_columns = [
        "iceberg_id",
        "start_time",
        "end_time",
        "start_latitude",
        "start_longitude",
        "observed_latitude",
        "observed_longitude",
        "displacement_m",
        "displacement_km",
        "azimuth_deg",
        "observed_u",
        "observed_v",
        "observed_speed",
        "duration_hours",
    ]

    missing_found = False

    for column in important_columns:
        if column not in df.columns:
            print(f"{column:25s} COLUMN MISSING")
            missing_found = True
            continue

        count = int(df[column].isna().sum())

        if count > 0:
            missing_found = True

        print(f"{column:25s} {count}")

    print("\n--- DUPLICATE CHECK ---")

    duplicate_pairs = df.duplicated(
        subset=["iceberg_id", "start_time", "end_time"],
        keep=False,
    )

    print(f"Duplicate pairs:    {duplicate_pairs.sum()}")

    if duplicate_pairs.any():
        print("\nDuplicate records:")
        print(
            df.loc[
                duplicate_pairs,
                ["iceberg_id", "start_time", "end_time"],
            ].to_string(index=False)
        )

    print("\n--- MOVEMENT CHECK ---")

    displacement_km = pd.to_numeric(
        df["displacement_km"], errors="coerce"
    )

    observed_speed = pd.to_numeric(
        df["observed_speed"], errors="coerce"
    )

    zero_threshold_km = 0.1

    zero_movement = displacement_km <= zero_threshold_km

    print(
        f"Nearly-zero displacement "
        f"(<= {zero_threshold_km} km): {zero_movement.sum()}"
    )

    print(
        f"Minimum displacement: {displacement_km.min():.3f} km"
    )

    print(
        f"Maximum displacement: {displacement_km.max():.3f} km"
    )

    print(
        f"Mean displacement:    {displacement_km.mean():.3f} km"
    )

    print(
        f"Median displacement:  {displacement_km.median():.3f} km"
    )

    print("\n--- SPEED CHECK ---")

    print(
        f"Minimum observed speed: {observed_speed.min():.6f} m/s"
    )

    print(
        f"Maximum observed speed: {observed_speed.max():.6f} m/s"
    )

    print(
        f"Mean observed speed:    {observed_speed.mean():.6f} m/s"
    )

    print(
        f"Median observed speed:  {observed_speed.median():.6f} m/s"
    )

    print("\n--- LARGE-MOVEMENT REVIEW ---")

    # Review only; do NOT automatically remove observations.
    large_threshold_km = 50.0

    large_movement = displacement_km >= large_threshold_km

    print(
        f"Pairs >= {large_threshold_km} km: "
        f"{large_movement.sum()}"
    )

    if large_movement.any():
        columns = [
            "iceberg_id",
            "start_time",
            "end_time",
            "displacement_km",
            "observed_speed",
            "azimuth_deg",
        ]

        print("\nLarge-movement pairs:")
        print(
            df.loc[
                large_movement,
                columns,
            ].sort_values(
                "displacement_km",
                ascending=False,
            ).to_string(index=False)
        )

    print("\n--- GEOGRAPHIC RANGE ---")

    for column in [
        "start_latitude",
        "observed_latitude",
        "start_longitude",
        "observed_longitude",
    ]:
        values = pd.to_numeric(df[column], errors="coerce")

        print(
            f"{column:25s}"
            f" min={values.min():.3f}"
            f" max={values.max():.3f}"
        )

    print("\n--- TIME CONTINUITY CHECK ---")

    continuity_problems = []

    for iceberg_id, group in df.groupby("iceberg_id"):
        group = group.sort_values("start_time").reset_index(drop=True)

        for i in range(1, len(group)):
            previous_end = group.loc[i - 1, "end_time"]
            current_start = group.loc[i, "start_time"]

            gap_hours = (
                current_start - previous_end
            ).total_seconds() / 3600.0

            if abs(gap_hours) > 0.001:
                continuity_problems.append(
                    (
                        iceberg_id,
                        previous_end,
                        current_start,
                        gap_hours,
                    )
                )

    print(
        f"Continuity problems: {len(continuity_problems)}"
    )

    if continuity_problems:
        for problem in continuity_problems:
            iceberg_id, previous_end, current_start, gap = problem

            print(
                f"{iceberg_id}: "
                f"{previous_end} -> {current_start} "
                f"gap={gap:.2f}h"
            )

    print("\n--- FINAL AUDIT STATUS ---")

    checks = {
        "105 total pairs": len(df) == 105,
        "15 selected icebergs": df["iceberg_id"].nunique() == 15,
        "7 pairs per selected iceberg": all_counts_correct,
        "All durations 24h": bool(duration_ok.all()),
        "No missing important values": not missing_found,
        "No duplicate pairs": not duplicate_pairs.any(),
        "No continuity problems": len(continuity_problems) == 0,
    }

    all_pass = True

    for name, passed in checks.items():
        status = "PASS" if passed else "CHECK"

        if not passed:
            all_pass = False

        print(f"{status:7s} {name}")

    print("\n" + "=" * 70)

    if all_pass:
        print("BYU AUDIT RESULT: PASS")
        print(
            "The selected calibration observations are structurally "
            "consistent."
        )
    else:
        print("BYU AUDIT RESULT: REVIEW REQUIRED")
        print(
            "One or more structural checks require investigation."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()