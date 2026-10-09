import requests, pandas as pd

def fetch(lat, lon, start="2023-01-01", end="2023-12-31"):
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": "shortwave_radiation,direct_normal_irradiance,"
                  "temperature_2m,cloud_cover,wind_speed_100m",
        "wind_speed_unit": "ms", "timezone": "UTC",
    }, timeout=60)
    r.raise_for_status()
    j = r.json()
    df = pd.DataFrame(j["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    print(j.get("hourly_units"))
    return df.set_index("time")

for name, lat, lon in [("Ouarzazate", 30.99, -6.86), ("Tarfaya", 27.9, -12.9)]:
    df = fetch(lat, lon)
    print("\n==", name, df.shape)
    print(df.isna().sum().to_dict())                     # missing values?
    print(df.describe().round(1))
    print("GHI kWh/m2/year:", round(df.shortwave_radiation.sum() / 1000))
    print("Mean wind 100m (m/s):", round(df.wind_speed_100m.mean(), 1))
    print(df.resample("MS").mean().round(1)[["shortwave_radiation", "wind_speed_100m"]])
    df.to_parquet(f"{name}_2023.parquet", compression="zstd")