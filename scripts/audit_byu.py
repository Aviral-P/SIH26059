import zipfile
import pandas as pd
from collections import Counter

ZIP_PATH = "data/raw/byu/stats_database_v7.1.zip"

print("===== BYU STATS DATABASE AUDIT =====")

with zipfile.ZipFile(ZIP_PATH) as z:
    csv_files = [
        name for name in z.namelist()
        if name.lower().endswith(".csv")
    ]

    print(f"\nCSV files: {len(csv_files)}")

    column_sets = Counter()
    total_rows = 0

    for i, filename in enumerate(csv_files):
        with z.open(filename) as f:
            df = pd.read_csv(f)

        total_rows += len(df)
        column_sets[tuple(df.columns)] += 1

        if i < 5:
            print(f"\n--- {filename} ---")
            print("Rows:", len(df))
            print("Columns:", list(df.columns))
            print(df.head(3).to_string(index=False))

    print("\n===== SUMMARY =====")
    print("Total rows:", total_rows)

    print("\nColumn structures:")
    for columns, count in column_sets.items():
        print(f"{count} files:")
        print(" ", columns)