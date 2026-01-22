"""Complete BGSAXO Excel Analysis"""
import pandas as pd
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")

files = {
    "Posizioni": "Posizioni_03-gen-2026_08_09_47.xlsx",
    "Transactions": "Transactions_19807401_2024-11-26_2026-01-03.xlsx",
    "Trades": "Trades_19807401_2024-11-26_2026-01-03.xlsx",
    "CashTransfers": "CashTransfers_19807401_2024-11-26_2026-01-03.xlsx"
}

report = []

for name, fname in files.items():
    fpath = INBOX / fname
    df = pd.read_excel(fpath, engine='calamine')
    
    report.append(f"\n{'='*70}")
    report.append(f"📂 {name.upper()}")
    report.append(f"   File: {fname}")
    report.append(f"   Rows: {len(df)} | Columns: {len(df.columns)}")
    report.append(f"{'='*70}")
    
    report.append("\nCOLUMNS:")
    for i, col in enumerate(df.columns):
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        if non_null > 0:
            sample = str(df[col].dropna().iloc[0])[:50]
        else:
            sample = "N/A"
        report.append(f"  [{i:2}] {col:40} | {dtype:10} | sample: {sample}")
    
    # Show first row as example
    report.append("\nFIRST ROW SAMPLE:")
    for col in df.columns[:10]:  # First 10 columns only
        val = df[col].iloc[0] if len(df) > 0 else "N/A"
        report.append(f"  {col}: {val}")
    if len(df.columns) > 10:
        report.append(f"  ... and {len(df.columns) - 10} more columns")

# Write report
output_path = Path(r"d:\Download\Progetto WAR ROOM\warroom\bgsaxo_excel_analysis.md")
with open(output_path, 'w', encoding='utf-8') as f:
    f.write("# BGSAXO Excel Files Analysis\n\n")
    f.write("\n".join(report))

print(f"Report saved to: {output_path}")
print("\n".join(report[:60]))  # Show first 60 lines in console
