import time, json, os, requests, pandas as pd

grid = pd.read_csv("data/grid.csv")
CACHE = "data/geocode_cache.json"
cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
H = {"User-Agent": "solar-pv-portfolio-project (student project)"}

for i, r in grid.iterrows():
    if r.site_id in cache:
        continue
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/reverse", headers=H, timeout=30,
            params={"lat": r.lat, "lon": r.lon, "format": "jsonv2", "zoom": 10, "accept-language": "fr"})
        a = resp.json().get("address", {})
    except Exception as e:
        print("error", r.site_id, e); a = {}
    cache[r.site_id] = a
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    print(i + 1, "/", len(grid), r.site_id, a.get("state"), "|", a.get("county"))
    time.sleep(1.1)

def pick(a, *keys):
    for k in keys:
        if a.get(k):
            return a[k]
    return None

grid["place"] = [pick(cache[s], "city", "town", "village", "municipality", "county") for s in grid.site_id]
grid["province"] = [pick(cache[s], "county", "state_district") for s in grid.site_id]
grid["region"] = [pick(cache[s], "state") for s in grid.site_id]
grid["country"] = [pick(cache[s], "country") for s in grid.site_id]
grid.to_csv("data/dim_site.csv", index=False, encoding="utf-8")
print(grid.region.value_counts(dropna=False))
