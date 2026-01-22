"""Extract and display BG Saxo CSV structure cleanly."""
import pandas as pd

csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine='python')

# Clean column names
clean_cols = [c.replace('\ufeff', '').replace('"', '').strip() for c in df.columns]
df.columns = clean_cols

print("="*60)
print("BG SAXO CSV ANALYSIS")
print("="*60)
print(f"Total Rows: {len(df)}")
print(f"Total Columns: {len(df.columns)}")
print()

print("ALL COLUMNS:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2}. {col}")

print()
print("="*60)
print("SAMPLE DATA (First Row):")
print("="*60)
for col in df.columns:
    val = df.iloc[0][col]
    print(f"  {col}: {val}")

print()
print("="*60)
print("KEY FIELDS FOR INGESTION:")
print("="*60)
key_cols = ['Strumento', 'Valuta', 'Quantità', 'Prezzo di apertura', 'Prz. corrente', 'ISIN', 'Emittente', 'Tipo attività']
existing = [c for c in key_cols if c in df.columns]
print(df[existing].head(10).to_string())
