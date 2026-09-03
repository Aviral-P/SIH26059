import zipfile
import pandas as pd
import psycopg2
from io import StringIO

ZIP_PATH = "data/raw/byu/stats_database_v7.1.zip"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "antarctic_nav",
    "user": "antarctic",
    "password": "antarctic_dev_password",
}

INSERT_SQL = """
INSERT INTO iceberg_trajectories (
    source,
    iceberg_id,
    observed_at,
    latitude,
    longitude,
    displacement_km,
    velocity_angle_deg,
    geometry
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s,
    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
)
"""

def parse_date(value):
    """
    BYU date format is YYYYDDD.
    Example:
        2011114 = 2011 + day 114
    """
    value = str(int(value))
    year = int(value[:4])
    day_of_year = int(value[4:])

    return pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(
        days=day_of_year - 1
    )


print("===== BYU → POSTGIS INGESTION =====")

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

total_inserted = 0

with zipfile.ZipFile(ZIP_PATH) as z:

    csv_files = sorted(
        name for name in z.namelist()
        if name.lower().endswith(".csv")
    )

    print("CSV files:", len(csv_files))

    for index, filename in enumerate(csv_files, start=1):

        iceberg_id = filename.split("/")[-1].replace(".csv", "")

        print(
            f"[{index}/{len(csv_files)}] "
            f"{iceberg_id}"
        )

        with z.open(filename) as f:
            df = pd.read_csv(f)

        rows = []

        for _, row in df.iterrows():

            lat = float(row["lat"])
            lon = float(row["lon"])

            # Coordinate validation
            if not (-90 <= lat <= 90):
                continue

            if not (-180 <= lon <= 180):
                continue

            observed_at = parse_date(row["date"])

            displacement = (
                float(row["disp"])
                if pd.notna(row["disp"])
                else None
            )

            velocity_angle = (
                float(row["vel_angle"])
                if pd.notna(row["vel_angle"])
                else None
            )

            rows.append((
                "BYU_STATS_V7.1",
                iceberg_id,
                observed_at,
                lat,
                lon,
                displacement,
                velocity_angle,
                lon,
                lat,
            ))

        cur.executemany(INSERT_SQL, rows)

        conn.commit()

        total_inserted += len(rows)

print("\n===== COMPLETE =====")
print("Rows inserted:", total_inserted)

cur.close()
conn.close()