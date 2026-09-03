import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "antarctic_nav",
    "user": "antarctic",
    "password": "antarctic_dev_password",
}

print("===== BUILDING ICEBERG TRACKS =====")

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Remove previously generated tracks so the script is safely re-runnable.
cur.execute("TRUNCATE TABLE iceberg_tracks RESTART IDENTITY;")

cur.execute("""
    INSERT INTO iceberg_tracks (
        source,
        iceberg_id,
        start_time,
        end_time,
        point_count,
        track_geometry
    )
    SELECT
        source,
        iceberg_id,
        MIN(observed_at),
        MAX(observed_at),
        COUNT(*),
        ST_MakeLine(
            geometry
            ORDER BY observed_at
        )
    FROM iceberg_trajectories
    GROUP BY source, iceberg_id
    HAVING COUNT(*) >= 2;
""")

conn.commit()

cur.execute("""
    SELECT
        COUNT(*) AS tracks,
        SUM(point_count) AS points
    FROM iceberg_tracks;
""")

tracks, points = cur.fetchone()

print(f"Tracks created : {tracks}")
print(f"Points covered : {points}")

cur.close()
conn.close()

print("\n===== COMPLETE =====")