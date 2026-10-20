# Solar PV Site Screening, Morocco

A screening model that ranks 247 locations across Morocco for solar PV by combining
**energy yield** (what a panel would produce) and **grid access** (distance to the
nearest substation). Stack: Python, PostgreSQL, Power BI.

MODEL
![alt text](image-8.png)
MODEL VS REALITY
![alt text](image-7.png)
## Results at a glance

| Hypothesis | Result |
|---|---|
| **H1.** The highest yield is in the far south | **Confirmed.** 6 of the top 10 sites are in Dakhla-Oued Ed-Dahab. |
| **H2.** Adding grid distance changes the ranking | **Partly.** Rank correlation 0.76; 8 of the top 10 stay the same. |
| **H3.** The ranking is robust to the weights | **Confirmed in the range tested.** 9 sites are in the top 10 in at least 5 of 7 weight settings. |
| **H4.** The model matches where real plants were built | **Partly.** It agrees in the far south and disagrees in the interior. |

Annual yield: 1,499 to 1,878 kWh/kWp across sites (mean about 1,711).

## 1. Data sources

| Data | Source | Period / size | Used for |
|---|---|---|---|
| Hourly weather: shortwave radiation, temperature at 2 m, wind at 100 m, direct normal irradiance | ERA5 reanalysis [via ... , access date] | 2023, 247 sites x 8,760 h = 2,163,720 rows | Yield model |
| Substations | OpenStreetMap [Overpass, access date] | 622 objects, 270 with a voltage tag | Grid distance |
| Solar plants | OpenStreetMap [access date] | 490 objects; 10 have a capacity of 1 MW or more | H4 (reality check) |
| Site grid | Generated: regular 0.5 degree lattice over Morocco | 247 points (G-0067 excluded: region unreliable) | Candidate sites |

Direct normal irradiance is loaded but not used in the yield; it is kept to test the
CSP explanation for H4. Only 11 of 490 OSM solar objects carry a capacity tag, so the
plant sample is small.

## 2. Pipeline and data model

**Layers.** Raw hourly files per site (bronze, parquet, never edited) -> computed
yields per site (silver, CSV, rebuilt from bronze) -> PostgreSQL star schema ->
Power BI. Raw data is kept so the model can be recomputed when an assumption changes,
without downloading again.

**PostgreSQL star schema**

| Table | Rows | Role | Main columns |
|---|---|---|---|
| `dim_site` | 247 | Dimension | `site_id`, `lat`, `lon`, `label` (e.g. "27 km SW of Ifrane"), `nearest_place`, `dist_km`, `direction`, `region` (12), `substation_km`, `hv_substation_km` |
| `fact_hourly` | 2,163,720 | Fact | `site_id`, `ts` (UTC), `shortwave_radiation`, `direct_normal_irradiance`, `temperature_2m`, `wind_speed_100m` |
| `dim_substation` | 622 | Dimension | location, `voltage_kv` |
| `dim_solar_plant` | 10 (1 MW or more) | Dimension | `name`, `capacity_mw`, `lat`, `lon` |

`fact_hourly.site_id` joins to `dim_site.site_id`.

**Power BI model**

| Table | Source | Relationship |
|---|---|---|
| Sites | `dim_site` | one-to-many to Hourly Weather on `site_id`; one-to-one to Site Yield |
| Hourly Weather | `fact_hourly` | many side |
| Site Yield | `site_features.csv` (Python yield per site) | one-to-one with Sites |
| Solar Plants | `solar_plants.csv`, filtered to 1 MW or more | none |
| Plant Ranks | `plant_ranks.csv` (Python ranks) | none |
| Map Points | calculated table: top 10 by yield + real plants | none |

## 3. Method

**Yield (per hour, per site, then summed over the year)**
```
wind10  = wind100 x 0.708
Tcell   = T + G / (25 + 6.84 x wind10)
kWh/kWp = G / 1000 x 0.86 x (1 - 0.004 x (Tcell - 25))
```
`G` is radiation in W/m2. Panels are assumed fixed and horizontal. 0.86 is a typical
performance ratio (an assumption, applied to all sites equally), and 0.4% per degree
is the usual silicon temperature loss.

**Score**
```
Score = 100 x ( w x YieldNorm + (1 - w) x (1 - GridNorm) )
```
Both inputs are min-max scaled to 0 to 1 over all 247 sites. Default `w` = 0.6.
Grid distance = nearest HV substation (60 kV or more), falling back to the nearest
substation of any voltage. It is a proxy: it ignores line capacity.

**DAX measures.** `Yield Norm` and `Grid Norm` use `ALL()` for the min and max, so
filtering by region does not rescale the scores. `Site Score` combines them with the
weight slider.

**Cross-check.** Yield and score were built in both Python and DAX. The best yield
matches (1,878.04 vs 1,878.05 kWh/kWp) and the top 10 by score matches at w = 0.6.

## 4. Power BI analysis: the four hypotheses

### H1. The highest yield is in the far south: confirmed

**Analysis.** Yield was computed for every site and ranked on page 1 (map, top
sites table, average yield by region).

**Result.** Of the top 10 sites by yield: 6 in Dakhla-Oued Ed-Dahab, 2 in
Souss-Massa, 1 in Beni Mellal-Khenifra, 1 in Laayoune-Sakia El Hamra. One of the
top sites (G-0157, near Ifrane) has a region label that may be unreliable near a
border.

![alt text](image-1.png)

### H2. Adding grid distance changes the ranking: partly

**Analysis.** Sites were ranked by yield alone and by the score (w = 0.6), then
compared. Page 2 shows the top 10 by score and a scatter of grid distance against
yield.

**Result.** Rank correlation 0.76, and 8 of the top 10 sites are the same. The top
southern sites are only 14 to 51 km from a substation, so the grid term does not
remove them.

![alt text](image-2.png)

### H3. The ranking is robust to the weights: confirmed in the range tested

**Analysis.** The yield weight was varied from 0.9 to 0.3 in 7 steps, and the top 10
was recorded at each step. The page 2 slider reproduces this live.

**Result.** 9 sites are in the top 10 in at least 5 of 7 settings. This holds only
inside the range tested.

![alt text](image-3.png)
![alt text](image-4.png)

### H4. The model matches where real plants were built: partly

**Analysis.** The 10 OSM plants of 1 MW or more were each matched to their nearest
grid cell, and that cell's rank was read, by yield and by score (1 = best of 247).
The map shows the 10 highest-yield sites against the real plants.

| Plant | Nearest cell | Rank by yield | Rank by score |
|---|---|---|---|
| Noor Boujdour (20 MW) | G-0056 | 5 | 5 |
| Noor Laayoune (85 MW) | G-0078 | 91 | 31 |
| Noor Zagora (40 MW) | G-0136 | 167 | 117 |
| Noor Erfoud (40 MW) | G-0161 | 172 | 135 |
| Noor Missour (40 MW) | G-0201 | 201 | 170 |
| Noor Ouarzazate (several phases, one cell) | G-0144 | 145 | 85 |

**Result.** The far-south plants are in the model's top area (Boujdour is on a
top-10 cell; Laayoune ranks 31 by score). The interior plants rank between 85 and
170. Adding the grid improves the rank of every plant except Boujdour, which is
already at 5. This is partly built in, because plants are often built near
substations.

**Possible reasons for the interior mismatch (not tested).** The Ouarzazate complex
includes concentrated solar (CSP), which depends on direct sunlight rather than the
flat-panel radiation used here; this cannot explain the three interior PV plants.
Land, water and policy are not modelled, and ERA5 smooths the Atlas terrain.

**Limits.** The 10 plants fall in about 7 independent cells, so no statistic is
computed. The 582 MW OSM entry is the whole Ouarzazate complex, not one plant. One
OSM object has no name and is in the far north.

![alt text](image-6.png)
![alt text](image-5.png)
## 5. Limitations

- Screening model, not a bankable estimate: fixed horizontal panels, one year (2023),
  a 0.5 degree grid.
- Grid distance is a straight-line proxy; OSM is incomplete (270 of 622 substations
  have a voltage).
- Not modelled: land, water, price, financing, policy.
- Plant capacities and technologies come from OSM and should be checked against MASEN.

## 6. Next steps

Validate against PVGIS on 3 to 5 sites, repeat for another year, use direct normal
irradiance to test the CSP explanation, add panel tilt.