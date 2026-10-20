import time, sys, requests, pandas as pd
from pathlib import Path

YEAR = 2023
OUT = Path(f"data/bronze/year={YEAR}"); OUT.mkdir(parents=True, exist_ok=True)
URL = "https://archive-api.open-meteo.com/v1/archive"
VARS = "shortwave_radiation,direct_normal_irradiance,temperature_2m,wind_speed_100m"
PAUSE = 25   # seconds; keeps ~180 requests/hour, under the 5,000 weighted/hour limit

grid = pd.read_csv("data/grid.csv")
for i, r in grid.iterrows():
    f = OUT / f"{r.site_id}.parquet"
    if f.exists():
        continue
    for attempt in range(5):
        try:
            resp = requests.get(URL, timeout=60, params={
                "latitude": r.lat, "longitude": r.lon,
                "start_date": f"{YEAR}-01-01", "end_date": f"{YEAR}-12-31",
                "hourly": VARS, "wind_speed_unit": "ms", "timezone": "UTC"})
            if resp.status_code == 429:
                print("rate limited, waiting 5 min:", resp.text[:120])
                time.sleep(300); continue
            resp.raise_for_status()
            df = pd.DataFrame(resp.json()["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            for c in df.columns.drop("time"):
                df[c] = df[c].astype("float32")
            df.insert(0, "site_id", r.site_id)
            df.to_parquet(f, compression="zstd", index=False)
            print(f"{i+1}/{len(grid)} {r.site_id} ok", flush=True)
            break
        except Exception as e:
            print("error:", e); time.sleep(30)
    time.sleep(PAUSE)