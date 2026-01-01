"""
Compare Scalable Data: Raw JSON vs Database
Purpose: Identify gaps and determine if we should fix extraction or clean DB.
"""
from pathlib import Path
import sys
import json
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction, Holding
import pandas as pd

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

def main():
    # 1. Load extraction_results.json (Scalable only)
    json_path = Path(__file__).parent.parent / "extraction_results.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    scalable_rows = [r for r in all_data if r.get("broker") == "SCALABLE"]
    
    print("="*80)
    print("📄 EXTRACTION RESULTS (Scalable Only)")
    print("="*80)
    print(f"Total Scalable Rows: {len(scalable_rows)}")
    print("\n--- Sample Rows (First 5) ---")
    
    for i, row in enumerate(scalable_rows[:5]):
        print(f"\n[Row {i+1}]")
        print(f"  Date: {row.get('date')}")
        print(f"  Symbol: {row.get('symbol')}")
        print(f"  Operation: {row.get('operation')}")
        print(f"  Amount: {row.get('amount')}")
        print(f"  Qty: {row.get('quantity')}")
        print(f"  Currency: {row.get('currency')}")
        print(f"  Asset Type: {row.get('asset_type')}")
    
    # Check for required fields
    print("\n--- Field Coverage Check ---")
    required_fields = ['date', 'symbol', 'operation', 'amount', 'quantity', 'currency']
    for field in required_fields:
        empty_count = sum(1 for r in scalable_rows if not r.get(field) or r.get(field) in [0, 0.0, "", "UNKNOWN"])
        print(f"  {field}: {len(scalable_rows) - empty_count}/{len(scalable_rows)} rows have data")
    
    # 2. Check DB - Transactions
    db = SessionLocal()
    
    print("\n" + "="*80)
    print("💾 DATABASE - TRANSACTIONS (Scalable Only)")
    print("="*80)
    
    tx_count = db.query(Transaction).filter(Transaction.broker == "SCALABLE").count()
    print(f"Total Scalable Transactions in DB: {tx_count}")
    
    if tx_count > 0:
        txs = db.query(Transaction).filter(Transaction.broker == "SCALABLE").limit(5).all()
        print("\n--- Sample Transactions (First 5) ---")
        for tx in txs:
            print(f"  {tx.timestamp.date()} | {tx.ticker} | {tx.operation} | {tx.total_amount} {tx.currency}")
    else:
        print("  (No Scalable transactions in DB yet)")
    
    # 3. Check DB - Holdings
    print("\n" + "="*80)
    print("💰 DATABASE - HOLDINGS (Scalable Only)")
    print("="*80)
    
    h_count = db.query(Holding).filter(Holding.broker == "SCALABLE").count()
    print(f"Total Scalable Holdings in DB: {h_count}")
    
    if h_count > 0:
        holdings = db.query(Holding).filter(Holding.broker == "SCALABLE").all()
        print("\n--- Holdings ---")
        for h in holdings:
            print(f"  {h.ticker} | Qty: {h.quantity} | Value: {h.current_value} {h.currency}")
    else:
        print("  (No Scalable holdings in DB yet)")
    
    db.close()
    
    # 4. Summary & Recommendation
    print("\n" + "="*80)
    print("📋 SUMMARY & RECOMMENDATION")
    print("="*80)
    
    # Check if data is sufficient
    ops_with_unknown = sum(1 for r in scalable_rows if r.get('operation') == "UNKNOWN")
    ops_buy = sum(1 for r in scalable_rows if r.get('operation') == "BUY")
    ops_sell = sum(1 for r in scalable_rows if r.get('operation') == "SELL")
    ops_fee = sum(1 for r in scalable_rows if r.get('operation') == "FEE")
    ops_dividend = sum(1 for r in scalable_rows if r.get('operation') == "DIVIDEND")
    ops_transfer = sum(1 for r in scalable_rows if r.get('operation') == "TRANSFER_IN")
    
    print(f"\nOperation Breakdown:")
    print(f"  BUY:         {ops_buy}")
    print(f"  SELL:        {ops_sell}")
    print(f"  FEE:         {ops_fee}")
    print(f"  DIVIDEND:    {ops_dividend}")
    print(f"  TRANSFER_IN: {ops_transfer}")
    print(f"  UNKNOWN:     {ops_with_unknown}")
    
    rows_missing_qty = sum(1 for r in scalable_rows if not r.get('quantity') or r.get('quantity') == 0)
    print(f"\nRows Missing Quantity: {rows_missing_qty}/{len(scalable_rows)}")
    
    if ops_with_unknown == 0 and tx_count == 0:
        print("\n✅ RECOMMENDATION: Data looks good! Clear DB and retry Loader.")
    elif ops_with_unknown > 0:
        print(f"\n⚠️ RECOMMENDATION: {ops_with_unknown} rows still have UNKNOWN operation. Review extraction.")
    else:
        print("\n🔍 Manual investigation needed.")

if __name__ == "__main__":
    main()
