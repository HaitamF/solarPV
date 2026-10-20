import io, os, pandas as pd, psycopg2
from dotenv import load_dotenv

load_dotenv()
EXCLUDE = {"G-0067"}
conn = psycopg2.connect(host="127.0.0.1", port=5433, dbname="solar", user="solar",
                        password=os.getenv("POSTGRES_PASSWORD"))
cur = conn.cursor()

sites = pd.read_csv("data/dim_site.csv")
sites = sites[~sites.site_id.isin(EXCLUDE)]

cur.execute("SELECT count(*) FROM dim_site")
if cur.fetchone()[0] == 0:
    cols = ["site_id", "lat", "lon", "nearest_place", "dist_km", "direction", "region", "label", "region_note"]
    buf = io.StringIO()
    sites[cols].to_csv(buf, index=False, header=False)
    buf.seek(0)
    cur.copy_expert("COPY dim_site (%s) FROM STDIN WITH (FORMAT csv)" % ",".join(cols), buf)
    conn.commit()
    print("dim_site loaded:", len(sites))

cur.execute("SELECT DISTINCT site_id FROM fact_hourly")
done = {r[0] for r in cur.fetchall()}

fcols = ["site_id", "ts", "shortwave_radiation", "direct_normal_irradiance", "temperature_2m", "wind_speed_100m"]
for n, sid in enumerate(sites.site_id, 1):
    if sid in done:
        continue
    df = pd.read_parquet(f"data/bronze/year=2023/{sid}.parquet").rename(columns={"time": "ts"})[fcols]
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, float_format="%.2f")
    buf.seek(0)
    cur.copy_expert("COPY fact_hourly (%s) FROM STDIN WITH (FORMAT csv)" % ",".join(fcols), buf)
    conn.commit()
    print(n, "/", len(sites), sid, len(df), "rows", flush=True)

cur.execute("SELECT count(*) FROM fact_hourly")
print("fact_hourly rows:", cur.fetchone()[0])
conn.close()
