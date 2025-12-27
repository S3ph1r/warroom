
import csv
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Config
CSV_FILE = Path(r"D:\Download\Binance\2025_05_17_19_26_07.csv")
OUTPUT_FILE = "scripts/binance_final.json"

def parse_date(date_str):
    # Format: 2023-01-09-01:00:00
    # or 2021-05-12 14:00:00 (Check variety)
    try:
        # Try format from inspection
        dt = datetime.strptime(date_str, "%Y-%m-%d-%H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except:
        # Try generic
        try:
             dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
             return dt.strftime("%Y-%m-%d")
        except:
             return date_str

def main():
    print(f"Ingesting Binance CSV: {CSV_FILE}")
    
    if not CSV_FILE.exists():
        print("File not found!")
        return
        
    transactions = []
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = parse_date(row.get('datetime_tz_CET', ''))
            
            # Sent -> Sell/Withdrawal
            sent_amt = row.get('sent_amount')
            sent_cur = row.get('sent_currency')
            
            # Received -> Buy/Deposit
            recv_amt = row.get('received_amount')
            recv_cur = row.get('received_currency')
            
            # Fee
            fee_amt = row.get('fee_amount')
            fee_cur = row.get('fee_currency')
            
            try:
                s_val = float(sent_amt) if sent_amt else 0.0
                r_val = float(recv_amt) if recv_amt else 0.0
                f_val = float(fee_amt) if fee_amt else 0.0
            except:
                continue
                
            # Logic:
            # 1. If Sent > 0: Create SELL transaction
            if s_val > 0:
                # If Sent Currency is EUR, it's a "Cost" for a Buy, not a Sell of Asset (unless Forex).
                # But reconciling crypto, "EUR" is usually ignored or treated as Cash.
                # If we track EUR, we add it. 
                # Let's track EVERYTHING.
                t = {
                    "date": date,
                    "type": "SELL",
                    "asset": sent_cur,
                    "quantity": -s_val, # Negative for Sell
                    "amount": 0.0, # Value not strictly needed if we track units
                    "source_row": row.get('type')
                }
                transactions.append(t)
                
            # 2. If Received > 0: Create BUY transaction
            if r_val > 0:
                t = {
                    "date": date,
                    "type": "BUY",
                    "asset": recv_cur,
                    "quantity": r_val, # Positive for Buy
                    "amount": 0.0,
                    "source_row": row.get('type')
                }
                transactions.append(t)
                
            # 3. Fee
            if f_val > 0:
                t = {
                    "date": date,
                    "type": "FEE",
                    "asset": fee_cur,
                    "quantity": -f_val,
                    "amount": 0.0,
                    "source_row": "FEE"
                }
                transactions.append(t)

    # Filter out fiat if user only wants crypto? 
    # User said "Binance".
    # Usually we want to ignore "EUR" ledger if we don't reconcile cash.
    # But let's keep it. Users checks total value.
    
    print(f"Extracted {len(transactions)} ledger entries.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"transactions": transactions}, f, indent=2)

if __name__ == "__main__":
    main()
