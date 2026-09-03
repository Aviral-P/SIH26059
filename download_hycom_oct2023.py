import os
import time
import requests
from datetime import date, timedelta

BASE_URL = "https://ncss.hycom.org/thredds/ncss/GLBy0.08/expt_93.0/uv3z/2023"

OUT_DIR = "data/raw/hycom"
os.makedirs(OUT_DIR, exist_ok=True)

start_date = date(2023, 10, 2)
end_date   = date(2023, 10, 31)

for i in range((end_date - start_date).days + 1):
    day = start_date + timedelta(days=i)
    day_str = day.isoformat()

    output = os.path.join(
        OUT_DIR,
        f"hycom_2023-10-{day.day:02d}.nc4"
    )

    if os.path.exists(output) and os.path.getsize(output) > 0:
        print(f"[SKIP] {day_str} already exists")
        continue

    params = {
        "var": ["water_u", "water_v"],
        "north": "-55.0000",
        "west": "0.0000",
        "east": "360.0000",
        "south": "-90.0000",
        "disableProjSubset": "on",
        "horizStride": "1",
        "time_start": f"{day_str}T00:00:00Z",
        "time_end": f"{day_str}T21:00:00Z",
        "timeStride": "1",
        "vertCoord": "0",
        "addLatLon": "true",
        "accept": "netcdf4",
    }

    print(f"\n[DOWNLOAD] {day_str}")

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=300
        )

        print("HTTP:", response.status_code)
        print("Size:", len(response.content) / 1024 / 1024, "MB")

        response.raise_for_status()

        with open(output, "wb") as f:
            f.write(response.content)

        print(f"[OK] Saved → {output}")

    except Exception as e:
        print(f"[ERROR] {day_str}: {e}")

    time.sleep(2)

print("\n===== DOWNLOAD COMPLETE =====")
