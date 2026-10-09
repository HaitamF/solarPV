import geopandas as gpd, numpy as np, pandas as pd
from shapely.geometry import Point

STEP = 0.5
world = gpd.read_file("data/countries/ne_50m_admin_0_countries.shp")
names = [c for c in ("NAME", "ADMIN", "NAME_EN") if c in world.columns]
mask = world[names[0]].isin(["Morocco", "W. Sahara"])
land = world[mask].unary_union

pts = [(round(la, 2), round(lo, 2))
       for la in np.arange(20.5, 36.0, STEP)
       for lo in np.arange(-17.5, -0.9, STEP)
       if land.contains(Point(lo, la))]

df = pd.DataFrame(pts, columns=["lat", "lon"])
df.insert(0, "site_id", [f"G-{i:04d}" for i in range(len(df))])
df.to_csv("data/grid.csv", index=False)
print(len(df), "points")
