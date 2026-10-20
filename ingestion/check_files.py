import glob, os, pandas as pd

bad = 0
files = glob.glob("data/bronze/year=2023/*.parquet")
for f in files:
    try:
        n = len(pd.read_parquet(f))
        if n < 8000:
            raise ValueError(f"only {n} rows")
    except Exception as e:
        print("removing", f, "->", e)
        os.remove(f)
        bad += 1
print("checked", len(files), "files, removed", bad, "bad files")
