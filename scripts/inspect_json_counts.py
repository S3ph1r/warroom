import json
import os

HOLDINGS_PATH = "data/extracted/Posizioni_19-dic-2025_17_49_12.csv.json"

if not os.path.exists(HOLDINGS_PATH):
    print("File not found.")
    exit()

with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('data', [])
etfs = [x for x in items if x.get('asset_type') == 'ETF']
stocks = [x for x in items if x.get('asset_type') == 'STOCK']

print(f"Total Items: {len(items)}")
print(f"ETFs: {len(etfs)}")
print(f"Stocks: {len(stocks)}")
print(f"Other: {len(items) - len(etfs) - len(stocks)}")
