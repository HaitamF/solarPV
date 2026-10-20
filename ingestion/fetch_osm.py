import os, re, time, requests, numpy as np, pandas as pd, psycopg2, geopandas as gpd
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from shapely.geometry import Point

load_dotenv(r"C:\Users\hp\OneDrive\Bureau\personal_projects\solarPV\.env")
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
H = {"User-Agent": "solar-pv-portfolio-project (student project)"}
Q = """[out:json][timeout:120];
nwr["power"="substation"](20.5,-17.5,36.0,-0.9);
out center tags;"""
CSV = "data/osm/substations.csv"
os.makedirs("data/osm", exist_ok=True)

if not os.path.exists(CSV):
    els = None
    for attempt in range(3):
        for url in MIRRORS:
            try:
                print("trying", url)
                r = requests.post(url, data={"data": Q}, headers=H, timeout=180)
                r.raise_for_status()
                els = r.json()["elements"]
                break
            except Exception as e:
                print("  failed:", str(e)[:90])
        if els is not None:
            break
        print("all mirrors failed, waiting 60 s")
        time.sleep(60)
    if els is None:
        raise SystemExit("Overpass unavailable, try again later")

    rows = []
    for e in els:
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if lat is None:
            continue
        t = e.get("tags", {})
        nums = [int(x) for x in re.findall(r"\d+", t.get("voltage", ""))]
        rows.append({"name": t.get("name"),
                     "voltage_kv": max(nums) / 1000 if nums else None,
                     "lat": lat, "lon": lon})
    subs = pd.DataFrame(rows)
    print(len(subs), "substations in the rectangle")

    world = gpd.read_file("data/countries/ne_50m_admin_0_countries.shp")
    col = [c for c in ("NAME", "ADMIN", "NAME_EN") if c in world.columns][0]
    land = world[world[col].isin(["Morocco", "W. Sahara"])].union_all().buffer(0.05)
    subs = subs[[land.contains(Point(lo, la)) for la, lo in zip(subs.lat, subs.lon)]]
    subs.to_csv(CSV, index=False, encoding="utf-8")

subs = pd.read_csv(CSV)
print(len(subs), "substations inside Morocco |", subs.voltage_kv.notna().sum(), "with a voltage tag")

conn = psycopg2.connect(host="127.0.0.1", port=5433, dbname="solar", user="solar",
                        password=os.getenv("POSTGRES_PASSWORD"))
cur = conn.cursor()
cur.execute("SELECT site_id, lat, lon FROM dim_site ORDER BY site_id")
sites = pd.DataFrame(cur.fetchall(), columns=["site_id", "lat", "lon"])

def hav(lat1, lon1, lat2, lon2):
    la1, lo1 = np.radians(lat1)[:, None], np.radians(lon1)[:, None]
    la2, lo2 = np.radians(lat2)[None, :], np.radians(lon2)[None, :]
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(h))

D = hav(sites.lat.values, sites.lon.values, subs.lat.values, subs.lon.values)
sites["substation_km"] = D.min(axis=1).round(1)
hv = (subs.voltage_kv >= 60).values
sites["hv_substation_km"] = D[:, hv].min(axis=1).round(1) if hv.any() else np.nan

cur.execute("ALTER TABLE dim_site ADD COLUMN IF NOT EXISTS substation_km REAL")
cur.execute("ALTER TABLE dim_site ADD COLUMN IF NOT EXISTS hv_substation_km REAL")
for r in sites.itertuples():
    hvk = None if pd.isna(r.hv_substation_km) else float(r.hv_substation_km)
    cur.execute("UPDATE dim_site SET substation_km=%s, hv_substation_km=%s WHERE site_id=%s",
                (float(r.substation_km), hvk, r.site_id))

cur.execute("DROP TABLE IF EXISTS dim_substation")
cur.execute("CREATE TABLE dim_substation (id SERIAL PRIMARY KEY, name TEXT, voltage_kv REAL, lat REAL, lon REAL)")
vals = [(None if pd.isna(r.name) else r.name, None if pd.isna(r.voltage_kv) else float(r.voltage_kv),
         float(r.lat), float(r.lon)) for r in subs.itertuples()]
execute_values(cur, "INSERT INTO dim_substation (name, voltage_kv, lat, lon) VALUES %s", vals)
conn.commit()
conn.close()
print(sites[["substation_km", "hv_substation_km"]].describe().round(1))
