import unicodedata, numpy as np, pandas as pd

cols = ["id","name","ascii","alt","lat","lon","fclass","fcode","cc","cc2",
        "admin1","admin2","admin3","admin4","pop","elev","dem","tz","mod"]

def fold(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.replace("Marrakesh", "Marrakech")

OK = {"Tanger-Tetouan-Al Hoceima", "Oriental", "Fes-Meknes", "Rabat-Sale-Kenitra",
      "Beni Mellal-Khenifra", "Casablanca-Settat", "Marrakech-Safi", "Draa-Tafilalet",
      "Souss-Massa", "Guelmim-Oued Noun", "Laayoune-Sakia El Hamra", "Dakhla-Oued Ed-Dahab"}

a1 = {}
for line in open("data/geonames/admin1.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    a1[p[0]] = fold(p[1])

pl = pd.concat([pd.read_csv(f"data/geonames/{c}.txt", sep="\t", header=None, names=cols,
                quoting=3, dtype=str, keep_default_na=False) for c in ("MA", "EH")], ignore_index=True)
pl["lat"] = pl.lat.astype(float)
pl["lon"] = pl.lon.astype(float)
pl["pop"] = pd.to_numeric(pl["pop"], errors="coerce").fillna(0)
pl["region"] = [a1.get(f"{c}.{a}") for c, a in zip(pl.cc, pl.admin1)]
P = pl[pl.fclass == "P"].reset_index(drop=True)
named = P[P["pop"] >= 1000].reset_index(drop=True)
regp = P[P.region.isin(OK)].reset_index(drop=True)
print(len(named), "named places |", len(regp), "places with a Moroccan region")

g = pd.read_csv("data/grid.csv")[["site_id", "lat", "lon"]]

def hav(lat1, lon1, lat2, lon2):
    la1, lo1 = np.radians(lat1)[:, None], np.radians(lon1)[:, None]
    la2, lo2 = np.radians(lat2)[None, :], np.radians(lon2)[None, :]
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(h))

D = hav(g.lat.values, g.lon.values, named.lat.values, named.lon.values)
i = D.argmin(axis=1)
dist = D[np.arange(len(g)), i]
near = named.iloc[i].reset_index(drop=True)

p_la, p_lo = np.radians(near.lat.values), np.radians(near.lon.values)
s_la, s_lo = np.radians(g.lat.values), np.radians(g.lon.values)
y = np.sin(s_lo - p_lo) * np.cos(s_la)
x = np.cos(p_la) * np.sin(s_la) - np.sin(p_la) * np.cos(s_la) * np.cos(s_lo - p_lo)
brg = (np.degrees(np.arctan2(y, x)) + 360) % 360
dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

g["nearest_place"] = near.ascii.values
g["dist_km"] = dist.round(1)
g["direction"] = [dirs[int(((b + 22.5) % 360) // 45)] for b in brg]
g["label"] = [f"{d:.0f} km {o} of {n}" for d, o, n in zip(dist, g.direction, g.nearest_place)]

DR = hav(g.lat.values, g.lon.values, regp.lat.values, regp.lon.values)
j = DR.argmin(axis=1)
ok = near.region.isin(OK).values
g["region"] = np.where(ok, near.region.values, regp.region.values[j])
g["region_note"] = np.where(ok, "region of nearest place",
        ["region of nearest place with a Moroccan region, %d km away" % d for d in DR[np.arange(len(g)), j]])

g.to_csv("data/dim_site.csv", index=False, encoding="utf-8")
print(len(g), "sites")
print(g.dist_km.describe().round(1))
print(g.region.value_counts())
print(g[["site_id", "lat", "lon", "label", "region"]].head(10).to_string())
print(g[g.site_id == "G-0067"][["site_id", "label", "region", "region_note"]].to_string())
