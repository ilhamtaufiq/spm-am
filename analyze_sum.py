import pandas as pd

df = pd.read_excel('SPM Air Minum Cianjur.xlsx', header=None, skiprows=5)
sr_col = 21

# 1. Total sum from ALL rows
total_all = pd.to_numeric(df[sr_col], errors='coerce').fillna(0).round().sum()
print(f"Total SR (All Rows): {total_all}")

# 2. Total sum from rows where column 0 (No Urut) is NOT empty
valid_rows = df[df[0].notna() & (df[0] != "")]
total_valid = pd.to_numeric(valid_rows[sr_col], errors='coerce').fillna(0).round().sum()
print(f"Total SR (Valid No Urut): {total_valid}")

# 3. Identify the rows that have SR but NO No Urut
skipped_rows = df[df[0].isna() | (df[0] == "")]
total_skipped = pd.to_numeric(skipped_rows[sr_col], errors='coerce').fillna(0).round().sum()
print(f"Total SR (Skipped Rows): {total_skipped}")

# 4. Total rows count
print(f"Total rows count: {len(df)}")
print(f"Valid rows count: {len(valid_rows)}")
