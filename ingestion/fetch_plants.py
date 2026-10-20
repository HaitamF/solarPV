import os, re, time, requests, numpy as np, pandas as pd, psycopg2, geopandas as gpd
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from shapely.geometry import Point

load_dotenv(r"C:\Users\hp\OneDrive\Bureau\personal_projects\solarPV\.env")
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter"]
H = {"User-Agent": "solar-pv-portfolio-project (student project)"}
Q = """[out:json][timeout:120];
(
  nwr["power"="plant"]["plant:source"="solar"](20.5,-17.5,36.0,-0.9);
  nwr["power"="generator"]["generator:source"="solar"](20.5,-17.5,36.0,-0.9);
);
out center tags;"""
CSV = "data/osm/solar_plants.csv"
os.makedirs("data/osm", exist_ok=True)

def mw(text):
    if not text:
        return None
    m = re.match(r"\s*([\d.,]+)\s*([kKMG]?W)", str(text))
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v * {"W": 1e-6, "kW": 1e-3, "MW": 1, "GW": 1e3}[m.group(2).replace("w", "W")]

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
        print("waiting 60 s"); time.sleep(60)
    if els is None:
        raise SystemExit("Overpass unavailable, try again later")

    rows = []
    for e in els:
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if lat is None:
            continue
        t = e.get("tags", {})
        cap = mw(t.get("plant:output:electricity") or t.get("generator:output:electricity"))
        rows.append({"name": t.get("name"), "operator": t.get("operator"),
                     "capacity_mw": cap, "lat": lat, "lon": lon})
    p = pd.DataFrame(rows)
    print(len(p), "solar objects in the rectangle")

    world = gpd.read_file("data/countries/ne_50m_admin_0_countries.shp")
    col = [c for c in ("NAME", "ADMIN", "NAME_EN") if c in world.columns][0]
    land = world[world[col].isin(["Morocco", "W. Sahara"])].union_all().buffer(0.05)
    p = p[[land.contains(Point(lo, la)) for la, lo in zip(p.lat, p.lon)]]

    p["cell"] = list(zip(p.lat.round(2), p.lon.round(2)))
    p = p.sort_values("capacity_mw", ascending=False, na_position="last").drop_duplicates("cell").drop(columns="cell")
    p.to_csv(CSV, index=False, encoding="utf-8")

p = pd.read_csv(CSV); p = p[p.capacity_mw >= 1].reset_index(drop=True)
print(len(p), "solar plants/generators inside Morocco after cleaning")
print(p.capacity_mw.notna().sum(), "with a capacity tag |", (p.capacity_mw >= 1).sum(), "of 1 MW or more")
print(p.sort_values("capacity_mw", ascending=False).head(15).to_string(index=False))

conn = psycopg2.connect(host="127.0.0.1", port=5433, dbname="solar", user="solar",
                        password=os.getenv("POSTGRES_PASSWORD"))
cur = conn.cursor()
cur.execute("SELECT site_id, lat, lon FROM dim_site ORDER BY site_id")
s = pd.DataFrame(cur.fetchall(), columns=["site_id", "lat", "lon"])

def hav(la1, lo1, la2, lo2):
    a, b = np.radians(la1)[:, None], np.radians(lo1)[:, None]
    c, d = np.radians(la2)[None, :], np.radians(lo2)[None, :]
    h = np.sin((c - a) / 2) ** 2 + np.cos(a) * np.cos(c) * np.sin((d - b) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(h))

D = hav(s.lat.values, s.lon.values, p.lat.values, p.lon.values)
s["plant_km"] = D.min(axis=1).round(1)
s["plants_50km"] = (D <= 50).sum(axis=1)

cur.execute("ALTER TABLE dim_site ADD COLUMN IF NOT EXISTS plant_km REAL")
cur.execute("ALTER TABLE dim_site ADD COLUMN IF NOT EXISTS plants_50km INT")
for r in s.itertuples():
    cur.execute("UPDATE dim_site SET plant_km=%s, plants_50km=%s WHERE site_id=%s",
                (float(r.plant_km), int(r.plants_50km), r.site_id))
cur.execute("DROP TABLE IF EXISTS dim_solar_plant")
cur.execute("CREATE TABLE dim_solar_plant (id SERIAL PRIMARY KEY, name TEXT, operator TEXT, capacity_mw REAL, lat REAL, lon REAL)")
vals = [(None if pd.isna(r.name) else r.name, None if pd.isna(r.operator) else r.operator,
         None if pd.isna(r.capacity_mw) else float(r.capacity_mw), float(r.lat), float(r.lon)) for r in p.itertuples()]
execute_values(cur, "INSERT INTO dim_solar_plant (name, operator, capacity_mw, lat, lon) VALUES %s", vals)
conn.commit()
conn.close()
print(s[["plant_km", "plants_50km"]].describe().round(1))
