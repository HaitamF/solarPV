import pandas as pd

df=pd.read_parquet(r"C:\Users\hp\OneDrive\Bureau\personal_projects\solarPV\data\bronze\year=2023\G-0001.parquet")
print(df.tail())
