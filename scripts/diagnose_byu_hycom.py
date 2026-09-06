from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


CALIBRATION_FILE = (
    ROOT / "data" / "catalog" / "calibration_observations.csv"
)

HYCOM_AUDIT_FILE = (
    ROOT / "data" / "catalog" / "hycom_sampling_audit.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "catalog" / "byu_hycom_diagnostics.csv"
)


def angle_difference_deg(a, b):
    """
    Smallest absolute difference between two directions in degrees.
    """
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def vector_direction_deg(u, v):
    """
    Direction measured clockwise from north.
    u = eastward component
    v = northward component
    """
    return (np.degrees(np.arctan2(u, v)) + 360.0) % 360.0


def main():

    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing calibration observations:\n{CALIBRATION_FILE}"
        )

    if not HYCOM_AUDIT_FILE.exists():
        raise FileNotFoundError(
            f"Missing HYCOM sampling audit:\n{HYCOM_AUDIT_FILE}"
        )

    byu = pd.read_csv(CALIBRATION_FILE)

    hycom = pd.read_csv(HYCOM_AUDIT_FILE)

    byu["start_time"] = pd.to_datetime(byu["start_time"])
    byu["end_time"] = pd.to_datetime(byu["end_time"])

    hycom["start_time"] = pd.to_datetime(hycom["start_time"])
    hycom["end_time"] = pd.to_datetime(hycom["end_time"])

    merged = byu.merge(
        hycom[
            [
                "iceberg_id",
                "start_time",
                "end_time",
                "complete_pair",
                "hycom_start_u",
                "hycom_start_v",
                "hycom_start_speed",
                "hycom_end_u",
                "hycom_end_v",
                "hycom_end_speed",
                "hycom_start_spatial_distance_km",
                "hycom_end_spatial_distance_km",
            ]
        ],
        on=[
            "iceberg_id",
            "start_time",
            "end_time",
        ],
        how="inner",
    )

    merged = merged[
        merged["complete_pair"] == True
    ].copy()

    print("=" * 80)
    print("BYU vs HYCOM CURRENT DIAGNOSTIC")
    print("=" * 80)

    print(f"\nComplete pairs available: {len(merged)}")

    if merged.empty:
        print("\nNo complete BYU-HYCOM pairs available.")
        return

    # ------------------------------------------------------------
    # HYCOM velocity averaged over start/end
    # ------------------------------------------------------------

    merged["hycom_mean_u"] = (
        merged["hycom_start_u"] +
        merged["hycom_end_u"]
    ) / 2.0

    merged["hycom_mean_v"] = (
        merged["hycom_start_v"] +
        merged["hycom_end_v"]
    ) / 2.0

    merged["hycom_mean_speed"] = np.sqrt(
        merged["hycom_mean_u"] ** 2 +
        merged["hycom_mean_v"] ** 2
    )

    # ------------------------------------------------------------
    # Observed velocity already comes from BYU
    # ------------------------------------------------------------

    merged["observed_speed"] = pd.to_numeric(
        merged["observed_speed"],
        errors="coerce"
    )

    merged["observed_u"] = pd.to_numeric(
        merged["observed_u"],
        errors="coerce"
    )

    merged["observed_v"] = pd.to_numeric(
        merged["observed_v"],
        errors="coerce"
    )

    # ------------------------------------------------------------
    # Speed ratio
    # ------------------------------------------------------------

    merged["observed_to_hycom_speed_ratio"] = np.where(
        merged["hycom_mean_speed"] > 0,
        merged["observed_speed"] /
        merged["hycom_mean_speed"],
        np.nan
    )

    # ------------------------------------------------------------
    # Direction comparison
    # ------------------------------------------------------------

    merged["observed_direction_deg"] = vector_direction_deg(
        merged["observed_u"],
        merged["observed_v"]
    )

    merged["hycom_direction_deg"] = vector_direction_deg(
        merged["hycom_mean_u"],
        merged["hycom_mean_v"]
    )

    merged["direction_difference_deg"] = [
        angle_difference_deg(a, b)
        for a, b in zip(
            merged["observed_direction_deg"],
            merged["hycom_direction_deg"]
        )
    ]

    # ------------------------------------------------------------
    # Component differences
    # ------------------------------------------------------------

    merged["u_difference"] = (
        merged["observed_u"] -
        merged["hycom_mean_u"]
    )

    merged["v_difference"] = (
        merged["observed_v"] -
        merged["hycom_mean_v"]
    )

    merged["vector_error"] = np.sqrt(
        merged["u_difference"] ** 2 +
        merged["v_difference"] ** 2
    )

    # ------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------

    u_corr = merged[
        ["observed_u", "hycom_mean_u"]
    ].corr().iloc[0, 1]

    v_corr = merged[
        ["observed_v", "hycom_mean_v"]
    ].corr().iloc[0, 1]

    speed_corr = merged[
        ["observed_speed", "hycom_mean_speed"]
    ].corr().iloc[0, 1]

    # ------------------------------------------------------------
    # Save
    # ------------------------------------------------------------

    merged.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------

    print("\n--- OBSERVED ICEBERG SPEED ---")

    print(
        f"Min:    {merged['observed_speed'].min():.6f} m/s"
    )

    print(
        f"Max:    {merged['observed_speed'].max():.6f} m/s"
    )

    print(
        f"Mean:   {merged['observed_speed'].mean():.6f} m/s"
    )

    print(
        f"Median: {merged['observed_speed'].median():.6f} m/s"
    )

    print("\n--- HYCOM CURRENT SPEED ---")

    print(
        f"Min:    {merged['hycom_mean_speed'].min():.6f} m/s"
    )

    print(
        f"Max:    {merged['hycom_mean_speed'].max():.6f} m/s"
    )

    print(
        f"Mean:   {merged['hycom_mean_speed'].mean():.6f} m/s"
    )

    print(
        f"Median: {merged['hycom_mean_speed'].median():.6f} m/s"
    )

    print("\n--- SPEED RATIO ---")

    ratio = merged[
        "observed_to_hycom_speed_ratio"
    ].dropna()

    print(
        f"Min:    {ratio.min():.3f}"
    )

    print(
        f"Max:    {ratio.max():.3f}"
    )

    print(
        f"Mean:   {ratio.mean():.3f}"
    )

    print(
        f"Median: {ratio.median():.3f}"
    )

    print("\n--- DIRECTION DIFFERENCE ---")

    print(
        f"Min:    "
        f"{merged['direction_difference_deg'].min():.2f}°"
    )

    print(
        f"Max:    "
        f"{merged['direction_difference_deg'].max():.2f}°"
    )

    print(
        f"Mean:   "
        f"{merged['direction_difference_deg'].mean():.2f}°"
    )

    print(
        f"Median: "
        f"{merged['direction_difference_deg'].median():.2f}°"
    )

    print("\n--- VELOCITY COMPONENT CORRELATION ---")

    print(f"U correlation:     {u_corr:.4f}")
    print(f"V correlation:     {v_corr:.4f}")
    print(f"Speed correlation: {speed_corr:.4f}")

    print("\n--- VECTOR ERROR ---")

    print(
        f"Mean:   "
        f"{merged['vector_error'].mean():.6f} m/s"
    )

    print(
        f"Median: "
        f"{merged['vector_error'].median():.6f} m/s"
    )

    print(
        f"Max:    "
        f"{merged['vector_error'].max():.6f} m/s"
    )

    print("\n--- BY ICEBERG ---")

    iceberg_summary = (
        merged
        .groupby("iceberg_id")
        .agg(
            pairs=("iceberg_id", "size"),
            observed_speed_mean=(
                "observed_speed",
                "mean"
            ),
            hycom_speed_mean=(
                "hycom_mean_speed",
                "mean"
            ),
            direction_difference_mean=(
                "direction_difference_deg",
                "mean"
            ),
            vector_error_mean=(
                "vector_error",
                "mean"
            ),
        )
        .sort_values(
            "vector_error_mean",
            ascending=False
        )
    )

    print(iceberg_summary.to_string())

    print("\n" + "=" * 80)
    print(f"Saved diagnostic: {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()