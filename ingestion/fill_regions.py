import numpy as np, pandas as pd

cols = ["id","name","ascii","alt","lat","lon","fclass","fcode","cc","cc2",
        "admin1","admin2","admin3","admin4","pop","elev","dem","tz","mod"]
a1 = {}
for line in open("data/geonames/admin1.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t"); a1[p[0]] = p[1]

pl = pd.concat([pd.read_csv(f"data/geonames/{c}.txt", sep="\t", header=None, names=cols,
                quoting=3, dtype=str, keep_default_na=False) for c in ("MA", "EH")], ignore_index=True)
pl["lat"] = pl.lat.astype(float); pl["lon"] = pl.lon.astype(float)
pl["region"] = [a1.get(f"{c}.{a}") for c, a in zip(pl.cc, pl.admin1)]
pl = pl[pl.region.notna()].reset_index(drop=True)

g = pd.read_csv("data/dim_site.csv")
g["region_note"] = "from nearest place"
miss = g.region.isna()
R = 6371.0
la1, lo1 = np.radians(g.lat[miss].values)[:, None], np.radians(g.lon[miss].values)[:, None]
la2, lo2 = np.radians(pl.lat.values)[None, :], np.radians(pl.lon.values)[None, :]
h = np.sin((la2-la1)/2)**2 + np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
D = 2*R*np.arcsin(np.sqrt(h)); i = D.argmin(axis=1)
g.loc[miss, "region"] = pl.region.values[i]
g.loc[miss, "region_note"] = [f"assigned from place with known region, {d:.0f} km away" for d in D[np.arange(len(i)), i]]
g.to_csv("data/dim_site.csv", index=False, encoding="utf-8")
print(g.region.value_counts(dropna=False))
print(g[g.region.str.contains("Tiris", na=False)][["site_id","lat","lon","label"]])
