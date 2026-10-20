import os, numpy as np, pandas as pd, psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\hp\OneDrive\Bureau\personal_projects\solarPV\.env")
conn = psycopg2.connect(host="127.0.0.1", port=5433, dbname="solar", user="solar",
                        password=os.getenv("POSTGRES_PASSWORD"))
d = pd.read_sql("SELECT site_id, lat, lon, label, region, substation_km, hv_substation_km, plant_km, plants_50km FROM dim_site", conn)
pl = pd.read_sql("SELECT name, capacity_mw, lat, lon FROM dim_solar_plant", conn)
f = pd.read_csv("data/silver/site_features.csv")[["site_id", "pv_kwh_per_kwp"]]
m = d.merge(f, on="site_id")
m["grid_km"] = m.hv_substation_km.fillna(m.substation_km)
n = len(m)
norm = lambda s: (s - s.min()) / (s.max() - s.min())

def score(w):
    return 100 * (w * norm(m.pv_kwh_per_kwp) + (1 - w) * (1 - norm(m.grid_km)))

m["rank_yield"] = m.pv_kwh_per_kwp.rank(ascending=False)
m["score60"] = score(0.6)
m["rank_score"] = m.score60.rank(ascending=False)
top = lambda col, k=10: set(m.nlargest(k, col).site_id)

print(f"{n} sites\n")
print("H1: where are the top 10 by yield?")
print(m.nlargest(10, "pv_kwh_per_kwp").region.value_counts().to_string())

print("\nH2: does the grid change the ranking?")
print("rank correlation yield vs score (Spearman):", round(m.rank_yield.corr(m.rank_score), 2))
print("top-10 sites in common:", len(top("pv_kwh_per_kwp") & top("score60")), "of 10")
print("regions in top 10 by score:")
print(m.nlargest(10, "score60").region.value_counts().to_string())

print("\nH3: is it robust to the weights? (yield weight from 0.9 to 0.3)")
ws = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
counts = {}
for w in ws:
    m["tmp"] = score(w)
    for s in top("tmp"):
        counts[s] = counts.get(s, 0) + 1
stable = [s for s, c in counts.items() if c >= 5]
print("sites in the top 10 in at least 5 of 7 weight sets:", len(stable))
print(m[m.site_id.isin(stable)][["site_id", "label", "region", "pv_kwh_per_kwp", "grid_km"]].round(0).to_string(index=False))

print("\nH4: where do real plants (1 MW or more) rank?")
P = pl[pl.capacity_mw >= 1]
rows = []
for r in P.itertuples():
    dist = np.hypot((m.lat - r.lat) * 111, (m.lon - r.lon) * 111 * np.cos(np.radians(r.lat)))
    i = dist.idxmin()
    rows.append({"plant": str(r.name)[:28], "mw": r.capacity_mw, "cell": m.site_id[i],
                 "cell_km": round(dist[i]), "rank_yield": int(m.rank_yield[i]), "rank_score": int(m.rank_score[i])})
print(pd.DataFrame(rows).to_string(index=False))
print("(rank 1 = best of", n, ")")
print("sites with a plant within 50 km:", int((m.plants_50km > 0).sum()))
conn.close()
