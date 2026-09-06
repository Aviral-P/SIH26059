from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from scripts.extract_environment import load_hycom, extract_hycom

OBS_FILE = ROOT / "data/catalog/calibration_observations.csv"
OUTPUT_FILE = ROOT / "data/catalog/hycom_calibration_coverage.csv"


def main():
    df = pd.read_csv(OBS_FILE)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    print("=" * 70)
    print("HYCOM COVERAGE TEST FOR ALL SELECTED CALIBRATION PAIRS")
    print("=" * 70)
    print(f"Total calibration pairs: {len(df)}")
    print(f"Unique icebergs: {df['iceberg_id'].nunique()}")
    print()

    # Cache datasets so the same HYCOM file is not repeatedly opened.
    dataset_cache = {}

    results = []

    for index, row in df.iterrows():

        iceberg_id = row["iceberg_id"]
        start_time = row["start_time"]
        end_time = row["end_time"]

        result = {
            "iceberg_id": iceberg_id,
            "start_time": start_time,
            "end_time": end_time,
            "start_hycom_available": False,
            "end_hycom_available": False,
            "start_extraction_available": False,
            "end_extraction_available": False,
            "pair_usable": False,
            "start_ocean_u": None,
            "start_ocean_v": None,
            "end_ocean_u": None,
            "end_ocean_v": None,
            "error": None,
        }

        print(
            f"[{index + 1:3}/{len(df)}] "
            f"{iceberg_id}: "
            f"{start_time.date()} -> {end_time.date()}",
            end=" "
        )

        try:
            # ----------------------------------------------------------
            # START TIME
            # ----------------------------------------------------------

            start_ds = load_hycom(start_time)

            result["start_hycom_available"] = True

            start_env = extract_hycom(
                start_ds,
                start_time,
                float(row["start_latitude"]),
                float(row["start_longitude"]),
            )

            result["start_extraction_available"] = bool(
                start_env["available"]
            )

            if start_env["available"]:
                result["start_ocean_u"] = start_env["u"]
                result["start_ocean_v"] = start_env["v"]

            # ----------------------------------------------------------
            # END TIME
            # ----------------------------------------------------------

            end_ds = load_hycom(end_time)

            result["end_hycom_available"] = True

            end_env = extract_hycom(
                end_ds,
                end_time,
                float(row["observed_latitude"]),
                float(row["observed_longitude"]),
            )

            result["end_extraction_available"] = bool(
                end_env["available"]
            )

            if end_env["available"]:
                result["end_ocean_u"] = end_env["u"]
                result["end_ocean_v"] = end_env["v"]

            # ----------------------------------------------------------
            # PAIR
            # ----------------------------------------------------------

            result["pair_usable"] = (
                result["start_extraction_available"]
                and result["end_extraction_available"]
            )

            if result["pair_usable"]:
                print("OK")
            else:
                print("PARTIAL")

        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            print("ERROR")

        results.append(result)

    # --------------------------------------------------------------
    # CLOSE DATASETS
    # --------------------------------------------------------------

    for ds in dataset_cache.values():
        try:
            ds.close()
        except Exception:
            pass

    result_df = pd.DataFrame(results)

    result_df.to_csv(OUTPUT_FILE, index=False)

    # --------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------

    total = len(result_df)

    usable = int(result_df["pair_usable"].sum())

    start_available = int(
        result_df["start_extraction_available"].sum()
    )

    end_available = int(
        result_df["end_extraction_available"].sum()
    )

    print()
    print("=" * 70)
    print("OVERALL RESULT")
    print("=" * 70)

    print(f"Total pairs:              {total}")
    print(f"Start extraction usable:  {start_available}")
    print(f"End extraction usable:    {end_available}")
    print(f"Complete pairs:            {usable}")
    print(
        f"Coverage:                  "
        f"{usable / total * 100:.1f}%"
    )

    # --------------------------------------------------------------
    # BY ICEBERG
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("COVERAGE BY ICEBERG")
    print("=" * 70)

    iceberg_summary = (
        result_df
        .groupby("iceberg_id")
        .agg(
            pairs=("iceberg_id", "size"),
            usable_pairs=("pair_usable", "sum"),
        )
    )

    iceberg_summary["coverage_pct"] = (
        iceberg_summary["usable_pairs"]
        / iceberg_summary["pairs"]
        * 100
    )

    print(iceberg_summary.to_string())

    # --------------------------------------------------------------
    # BY YEAR
    # --------------------------------------------------------------

    result_df["year"] = result_df["start_time"].dt.year

    print()
    print("=" * 70)
    print("COVERAGE BY YEAR")
    print("=" * 70)

    year_summary = (
        result_df
        .groupby("year")
        .agg(
            pairs=("iceberg_id", "size"),
            usable_pairs=("pair_usable", "sum"),
        )
    )

    year_summary["coverage_pct"] = (
        year_summary["usable_pairs"]
        / year_summary["pairs"]
        * 100
    )

    print(year_summary.to_string())

    # --------------------------------------------------------------
    # FAILED PAIRS
    # --------------------------------------------------------------

    failed = result_df[~result_df["pair_usable"]]

    print()
    print("=" * 70)
    print("UNUSABLE PAIRS")
    print("=" * 70)

    if failed.empty:
        print("None — all calibration pairs have usable HYCOM data.")
    else:
        print(
            failed[
                [
                    "iceberg_id",
                    "start_time",
                    "end_time",
                    "start_hycom_available",
                    "end_hycom_available",
                    "start_extraction_available",
                    "end_extraction_available",
                    "error",
                ]
            ].to_string(index=False)
        )

    print()
    print("=" * 70)
    print(f"Detailed output saved to:")
    print(OUTPUT_FILE)
    print("=" * 70)


if __name__ == "__main__":
    main()