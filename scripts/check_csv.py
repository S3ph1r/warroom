"""Verify CSV structure and find the correct way to read it"""
import pandas as pd

csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"

# Read raw to see structure
print("RAW CSV FIRST 5 LINES:")
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    for i, line in enumerate(f):
        if i < 5:
            print(f"Line {i}: {line[:150]}...")
        else:
            break

print()

# Try reading with skiprows
df = pd.read_csv(csv_path, encoding='utf-8-sig', skiprows=[1])
print(f"With skiprows=[1]: {len(df)} rows")

# Check first few rows
print()
print("FIRST 3 ROWS:")
for i in range(min(3, len(df))):
    row = df.iloc[i]
    strumento = row.iloc[0] if pd.notna(row.iloc[0]) else "N/A"
    valuta = row.iloc[2] if pd.notna(row.iloc[2]) else "N/A"
    qty = row.iloc[3] if pd.notna(row.iloc[3]) else 0
    prezzo = row.iloc[4] if pd.notna(row.iloc[4]) else 0
    print(f"  {i+1}. {str(strumento)[:30]} | {valuta} | qty={qty} | price={prezzo}")
