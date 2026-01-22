from db.database import SessionLocal
from db.models import Holding, Transaction
import sys

db = SessionLocal()

print("CHECKING HOLDINGS METADATA")
print("=" * 70)
print(f"{'TICKER':<20} | {'ISIN':<12} | {'RATIO':<5} | {'CLASS':<5} | {'NOM':<10} | {'MKT'}")
print("-" * 70)

holdings = db.query(Holding).all()
for h in holdings:
    r = str(h.adr_ratio) if h.adr_ratio else '-'
    c = str(h.share_class) if h.share_class else '-'
    n = str(h.nominal_value) if h.nominal_value else '-'
    m = str(h.market) if h.market else '-'
    isin_str = h.isin if h.isin else '-'
    print(f"{h.ticker:<20} | {isin_str:<12} | {r:<5} | {c:<5} | {n:<10} | {m}")

print("\nBROKERS IN DB:")
brokers = db.query(Transaction.broker).distinct().all()
for b in brokers:
    print(f" - '{b[0]}'")

print("\nSEARCHING FOR MISSING ASSETS IN DB (Alibaba, Midea, Hydrogen):")
missing_targets = ['ALIBABA', 'MIDEA', 'HYDROGEN', 'AHLA']
for h in holdings:
    if any(m in h.name.upper() or m in h.ticker.upper() for m in missing_targets):
        print(f" FOUND: {h.ticker} | {h.name} | Broker: {h.broker} | Type: {h.asset_type} | Qty: {h.quantity}")

print("\nCHECKING TRANSACTIONS METADATA")
print("=" * 70)
print(f"{'TICKER':<20} | {'ISIN':<12} | {'RATIO':<5} | {'CLASS':<5} | {'NOM':<10} | {'MKT'}")
print("-" * 70)

txs = db.query(Transaction).filter(Transaction.broker == "SCALABLE CAPITAL").limit(50).all()
for t in txs:
    r = str(t.adr_ratio) if t.adr_ratio else '-'
    c = str(t.share_class) if t.share_class else '-'
    n = str(t.nominal_value) if t.nominal_value else '-'
    m = str(t.market) if t.market else '-'
    isin_str = t.isin if t.isin else '-'
    print(f"{t.ticker:<20} | {isin_str:<12} | {r:<5} | {c:<5} | {n:<10} | {m}")

db.close()
print("=" * 70)
