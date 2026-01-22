"""Analyze extracted transactions"""
import json
from pathlib import Path
from collections import Counter

# Load JSON
data = json.loads(Path("data/extracted/BG_SAXO_Transactions_Full.json").read_text())
txns = data.get("transactions", [])

print(f"Total transactions in JSON: {len(txns)}")
print()

# Pages distribution
pages = Counter(t.get("_source_page", 0) for t in txns)
print(f"Transactions extracted from {len(pages)} pages")
print()

# Operations breakdown
ops = Counter(t.get("operation", "?") for t in txns)
print("Operations breakdown:")
for op, count in ops.most_common():
    print(f"  {op}: {count}")

print()

# Sample transactions from different pages
print("Sample transactions:")
for t in txns[:5]:
    print(f"  Page {t.get('_source_page')}: {t.get('date')} {t.get('operation')} {t.get('quantity')} x {t.get('ticker')}")
