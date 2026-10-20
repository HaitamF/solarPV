import glob, os, pandas as pd

PR_BASE, GAMMA = 0.86, -0.004      # system losses, PV power change per degree C (assumptions)
U0, U1 = 25.0, 6.84                # Faiman cell-temperature coefficients (commonly cited defaults)

rows = []
for f in sorted(glob.glob("data/bronze/year=2023/*.parquet")):
    d = pd.read_parquet(f).set_index("time")
    G, T = d.shortwave_radiation, d.temperature_2m
    v10 = d.wind_speed_100m * (10 / 100) ** 0.15        # rough 10 m wind (power-law assumption)
    t_cell = T + G / (U0 + U1 * v10)                     # wind cools the panel
    tf = 1 + GAMMA * (t_cell - 25)                       # temperature factor
    pv = G / 1000 * PR_BASE * tf                         # kWh per kWp per hour
    monthly = pv.resample("MS").sum()
    rows.append({
        "site_id": d.site_id.iloc[0],
        "ghi_kwh_m2": G.sum() / 1000,
        "dni_kwh_m2": d.direct_normal_irradiance.sum() / 1000,
        "pv_kwh_per_kwp": pv.sum(),
        "temp_loss_pct": 100 * (1 - tf[G > 50].mean()),
        "solar_cv": monthly.std() / monthly.mean(),
        "mean_temp": T.mean(),
        "mean_wind10": v10.mean(),
    })

feat = pd.DataFrame(rows).merge(pd.read_csv("data/grid.csv"), on="site_id")
os.makedirs("data/silver", exist_ok=True)
feat.round(3).to_csv("data/silver/site_features.csv", index=False)
print(feat.describe().round(1).T[["min", "mean", "max"]])
print(feat.sort_values("pv_kwh_per_kwp", ascending=False).head(10)[["site_id", "lat", "lon", "pv_kwh_per_kwp", "temp_loss_pct", "solar_cv"]])
