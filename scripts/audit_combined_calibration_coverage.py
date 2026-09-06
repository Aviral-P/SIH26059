from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

HYCOM_FILE = ROOT / "data/catalog/hycom_calibration_coverage.csv"
ERA5_FILE = ROOT / "data/catalog/era5_calibration_coverage.csv"
OUTPUT_FILE = ROOT / "data/catalog/combined_calibration_coverage.csv"


def normalize_keys(df):
    df = df.copy()

    df["start_time"] = pd.to_datetime(
        df["start_time"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df["end_time"] = pd.to_datetime(
        df["end_time"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    return df


def main():

    if not HYCOM_FILE.exists():
        raise FileNotFoundError(f"Missing: {HYCOM_FILE}")

    if not ERA5_FILE.exists():
        raise FileNotFoundError(f"Missing: {ERA5_FILE}")

    hycom = pd.read_csv(HYCOM_FILE)
    era5 = pd.read_csv(ERA5_FILE)

    hycom = normalize_keys(hycom)
    era5 = normalize_keys(era5)

    keys = [
        "iceberg_id",
        "start_time",
        "end_time",
    ]

    hycom_cols = keys + [
        "start_extraction_available",
        "end_extraction_available",
        "pair_usable",
    ]

    era5_cols = keys + [
        "start_available",
        "end_available",
        "complete",
    ]

    hycom_subset = hycom[hycom_cols].copy()
    era5_subset = era5[era5_cols].copy()

    merged = hycom_subset.merge(
        era5_subset,
        on=keys,
        how="inner",
    )

    merged["environment_complete"] = (
        merged["pair_usable"].astype(bool)
        & merged["complete"].astype(bool)
    )

    merged.to_csv(OUTPUT_FILE, index=False)

    print("=" * 60)
    print("COMBINED CALIBRATION COVERAGE")
    print("=" * 60)

    print(f"Total BYU pairs:       {len(merged)}")
    print(
        f"HYCOM complete:        "
        f"{merged['pair_usable'].sum()}"
    )
    print(
        f"ERA5 complete:         "
        f"{merged['complete'].sum()}"
    )
    print(
        f"Both complete:         "
        f"{merged['environment_complete'].sum()}"
    )

    if len(merged) > 0:
        coverage = (
            merged["environment_complete"].mean() * 100
        )
    else:
        coverage = 0.0

    print(f"Combined coverage:     {coverage:.1f}%")

    print()
    print("BY ICEBERG")
    print("-" * 60)

    iceberg_summary = (
        merged.groupby("iceberg_id")
        .agg(
            pairs=("iceberg_id", "size"),
            hycom_complete=("pair_usable", "sum"),
            era5_complete=("complete", "sum"),
            environment_complete=(
                "environment_complete",
                "sum",
            ),
        )
        .reset_index()
    )

    iceberg_summary["coverage_percent"] = (
        iceberg_summary["environment_complete"]
        / iceberg_summary["pairs"]
        * 100
    )

    print(iceberg_summary.to_string(index=False))

    print()
    print("BY YEAR")
    print("-" * 60)

    merged["year"] = pd.to_datetime(
        merged["start_time"]
    ).dt.year

    year_summary = (
        merged.groupby("year")
        .agg(
            pairs=("iceberg_id", "size"),
            hycom_complete=("pair_usable", "sum"),
            era5_complete=("complete", "sum"),
            environment_complete=(
                "environment_complete",
                "sum",
            ),
        )
        .reset_index()
    )

    year_summary["coverage_percent"] = (
        year_summary["environment_complete"]
        / year_summary["pairs"]
        * 100
    )

    print(year_summary.to_string(index=False))

    print()
    print("MISSING ENVIRONMENT PAIRS")
    print("-" * 60)

    missing = merged[
        ~merged["environment_complete"]
    ]

    if len(missing) == 0:
        print("None")
    else:
        print(
            missing[
                [
                    "iceberg_id",
                    "start_time",
                    "end_time",
                    "pair_usable",
                    "complete",
                ]
            ].to_string(index=False)
        )

    print()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()