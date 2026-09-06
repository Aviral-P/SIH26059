from pathlib import Path
import re
import zipfile

import pandas as pd
import numpy as np
import xarray as xr
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]

BYU_ZIP = ROOT / "data" / "raw" / "byu" / "stats_database_v7.1.zip"
NSIDC_DIR = ROOT / "data" / "raw" / "nsidc"
OUTPUT_FILE = ROOT / "data" / "catalog" / "nsidc_byu_overlap.csv"

START_DATE = pd.Timestamp("1978-10-26")
END_DATE = pd.Timestamp("2011-07-24")

TRANSFORMER = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:3412",
    always_xy=True,
)


def load_byu_observations():
    records = []

    with zipfile.ZipFile(BYU_ZIP, "r") as z:
        csv_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".csv")
        ]

        print(f"BYU CSV files found: {len(csv_files)}")

        for name in csv_files:
            try:
                with z.open(name) as f:
                    df = pd.read_csv(f)

                if df.empty:
                    continue

                required = ["date", "lat", "lon"]

                if not all(col in df.columns for col in required):
                    continue

                temp = df[["date", "lat", "lon"]].copy()

                # BYU v7.1 date format:
                # YYYYDDD
                # Example: 2011114 = 2011, day 114
                temp["date"] = pd.to_datetime(
                    temp["date"].astype(str),
                    format="%Y%j",
                    errors="coerce",
                )

                temp["lat"] = pd.to_numeric(
                    temp["lat"],
                    errors="coerce",
                )

                temp["lon"] = pd.to_numeric(
                    temp["lon"],
                    errors="coerce",
                )

                temp = temp.dropna(
                    subset=["date", "lat", "lon"]
                )

                temp = temp[
                    (temp["date"] >= START_DATE)
                    & (temp["date"] <= END_DATE)
                ]

                if temp.empty:
                    continue

                iceberg_id = Path(name).stem

                temp["iceberg_id"] = iceberg_id

                temp = temp.rename(
                    columns={
                        "lat": "latitude",
                        "lon": "longitude",
                    }
                )

                records.append(
                    temp[
                        [
                            "iceberg_id",
                            "date",
                            "latitude",
                            "longitude",
                        ]
                    ]
                )

            except Exception as exc:
                print(
                    f"Warning: could not read {name}: {exc}"
                )

    if not records:
        raise RuntimeError(
            "No BYU observations found in the NSIDC period."
        )

    result = pd.concat(
        records,
        ignore_index=True,
    )

    result = result.sort_values(
        ["iceberg_id", "date"]
    ).reset_index(drop=True)

    return result


def build_nsidc_index():
    index = {}

    files = list(NSIDC_DIR.glob("*.nc"))

    print(f"NSIDC NetCDF files found: {len(files)}")

    pattern = re.compile(r"_(\d{8})_")

    for path in files:
        match = pattern.search(path.name)

        if not match:
            continue

        date_key = match.group(1)

        if "NSIDC0051" not in path.name:
            continue

        index[date_key] = path

    print(f"NSIDC dates indexed: {len(index)}")

    return index


def detect_icecon_variable(ds):
    candidates = [
        "F17_ICECON",
        "ice_concentration",
        "sea_ice_concentration",
        "ICECON",
    ]

    for name in candidates:
        if name in ds.data_vars:
            return name

    for name in ds.data_vars:
        lower = name.lower()

        if (
            "icecon" in lower
            or "ice_con" in lower
        ):
            return name

    return None


def sample_nsidc(path, latitude, longitude):
    try:
        ds = xr.open_dataset(path)

        variable = detect_icecon_variable(ds)

        if variable is None:
            ds.close()
            return np.nan, False

        x, y = TRANSFORMER.transform(
            longitude,
            latitude,
        )

        if "x" not in ds.coords or "y" not in ds.coords:
            ds.close()
            return np.nan, False

        point = ds.sel(
            x=x,
            y=y,
            method="nearest",
        )

        value = point[variable].values

        if np.size(value) != 1:
            value = np.asarray(value).reshape(-1)[0]

        value = float(value)

        ds.close()

        if not np.isfinite(value):
            return np.nan, False

        return value, True

    except Exception:
        return np.nan, False


def main():
    print("=" * 70)
    print("BYU - NSIDC HISTORICAL OVERLAP AUDIT")
    print("=" * 70)

    if not BYU_ZIP.exists():
        raise FileNotFoundError(
            f"BYU database not found:\n{BYU_ZIP}"
        )

    if not NSIDC_DIR.exists():
        raise FileNotFoundError(
            f"NSIDC directory not found:\n{NSIDC_DIR}"
        )

    print()
    print("Loading BYU observations...")

    byu = load_byu_observations()

    print(
        f"BYU observations in NSIDC period: "
        f"{len(byu):,}"
    )

    print(
        f"BYU date range: "
        f"{byu['date'].min().date()} -> "
        f"{byu['date'].max().date()}"
    )

    print(
        f"Unique BYU icebergs: "
        f"{byu['iceberg_id'].nunique()}"
    )

    print()
    print("Building NSIDC date index...")

    nsidc_index = build_nsidc_index()

    print()
    print("Sampling NSIDC around BYU iceberg positions...")

    results = []

    total = len(byu)

    for i, row in enumerate(
        byu.itertuples(index=False),
        start=1,
    ):

        date_key = row.date.strftime("%Y%m%d")

        path = nsidc_index.get(date_key)

        if path is None:

            results.append(
                {
                    "iceberg_id": row.iceberg_id,
                    "date": row.date,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "nsidc_file": "",
                    "ice_concentration": np.nan,
                    "available": False,
                }
            )

        else:

            icecon, available = sample_nsidc(
                path,
                row.latitude,
                row.longitude,
            )

            results.append(
                {
                    "iceberg_id": row.iceberg_id,
                    "date": row.date,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "nsidc_file": path.name,
                    "ice_concentration": icecon,
                    "available": available,
                }
            )

        if i % 500 == 0 or i == total:
            print(
                f"Processed {i:,}/{total:,}"
            )

    result = pd.DataFrame(results)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    available_files = int(
        result["nsidc_file"].ne("").sum()
    )

    usable = int(
        result["available"].sum()
    )

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        f"BYU observations checked:    "
        f"{len(result):,}"
    )

    print(
        f"NSIDC files available:       "
        f"{available_files:,}"
    )

    print(
        f"Usable NSIDC samples:        "
        f"{usable:,}"
    )

    if len(result) > 0:

        print(
            f"File coverage:               "
            f"{available_files / len(result) * 100:.2f}%"
        )

        print(
            f"Usable coverage:             "
            f"{usable / len(result) * 100:.2f}%"
        )

    valid = result.loc[
        result["available"],
        "ice_concentration",
    ]

    if not valid.empty:

        print()
        print("=" * 70)
        print("SEA-ICE CONCENTRATION")
        print("=" * 70)

        print(
            f"Samples:                     "
            f"{len(valid):,}"
        )

        print(
            f"Mean:                        "
            f"{valid.mean():.4f}"
        )

        print(
            f"Median:                      "
            f"{valid.median():.4f}"
        )

        print(
            f"Minimum:                     "
            f"{valid.min():.4f}"
        )

        print(
            f"Maximum:                     "
            f"{valid.max():.4f}"
        )

    print()
    print("=" * 70)
    print("COVERAGE BY YEAR")
    print("=" * 70)

    result["year"] = result["date"].dt.year

    yearly = (
        result
        .groupby("year")
        .agg(
            observations=("date", "size"),
            nsidc_available=("available", "sum"),
        )
        .reset_index()
    )

    yearly["coverage_percent"] = (
        yearly["nsidc_available"]
        / yearly["observations"]
        * 100
    )

    print(
        yearly.to_string(
            index=False,
            formatters={
                "coverage_percent": "{:.2f}".format
            },
        )
    )

    print()
    print("=" * 70)
    print("COVERAGE BY ICEBERG")
    print("=" * 70)

    iceberg_summary = (
        result
        .groupby("iceberg_id")
        .agg(
            observations=("date", "size"),
            nsidc_available=("available", "sum"),
        )
        .reset_index()
    )

    iceberg_summary["coverage_percent"] = (
        iceberg_summary["nsidc_available"]
        / iceberg_summary["observations"]
        * 100
    )

    print(
        iceberg_summary.to_string(
            index=False,
            formatters={
                "coverage_percent": "{:.2f}".format
            },
        )
    )

    print()
    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)

    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()