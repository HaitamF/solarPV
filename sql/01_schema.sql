DROP TABLE IF EXISTS fact_hourly;
DROP TABLE IF EXISTS dim_site;

CREATE TABLE dim_site (
    site_id        TEXT PRIMARY KEY,
    lat            REAL NOT NULL,
    lon            REAL NOT NULL,
    nearest_place  TEXT,
    dist_km        REAL,
    direction      TEXT,
    region         TEXT,
    label          TEXT,
    region_note    TEXT
);

CREATE TABLE fact_hourly (
    site_id                   TEXT NOT NULL REFERENCES dim_site(site_id),
    ts                        TIMESTAMP NOT NULL,
    shortwave_radiation       REAL,
    direct_normal_irradiance  REAL,
    temperature_2m            REAL,
    wind_speed_100m           REAL,
    PRIMARY KEY (site_id, ts)
);

CREATE INDEX idx_fact_hourly_ts ON fact_hourly (ts);
