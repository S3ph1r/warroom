"""
Analyze transaction discrepancies
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction

db = SessionLocal()

# Look at XBOT transactions
txns = db.query(Transaction).filter(
    Transaction.broker=='bgsaxo', 
    Transaction.ticker.ilike('%XBOT%')
).all()

print(f"XBOT Transactions: {len(txns)}")
for t in txns[:20]:
    date = str(t.timestamp.date()) if t.timestamp else "?"
    print(f"  {date}: {t.operation} {t.quantity} @ {t.price}")

print()

# Also check for duplicates
txns_all = db.query(Transaction).filter(Transaction.broker=='bgsaxo').all()
print(f"Total BG SAXO transactions: {len(txns_all)}")

# Group by source document
from collections import Counter
sources = Counter(t.source_document for t in txns_all)
print("\nBy source document:")
for doc, count in sources.most_common(10):
    print(f"  {doc}: {count}")

db.close()
