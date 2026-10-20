import unicodedata, pandas as pd

g = pd.read_csv("data/dim_site.csv")
print("columns:", list(g.columns))

def fold(s):
    if pd.isna(s):
        return s
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.replace("Marrakesh", "Marrakech")

g["region"] = g.region.map(fold)
g.to_csv("data/dim_site.csv", index=False, encoding="utf-8")

print(g.region.value_counts())
show = [c for c in ("site_id", "lat", "lon", "nearest_place", "dist_km", "region_note") if c in g.columns]
print(g[g.region.str.contains("Tiris", na=False)][show].to_string())
