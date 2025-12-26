"""
Compare extracted Holdings/Transactions with Database baseline.
"""
import sys
from pathlib import Path
from sqlalchemy import select, func
from collections import defaultdict
import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import IngestionBatch, Holding, Transaction

def normalize_isin(isin):
    return isin.strip().upper() if isin else "UNKNOWN"

def get_latest_batches(session):
    """Get the latest ingestion batch for each file source."""
    # We want the latest successful extraction per file
    batches = session.scalars(
        select(IngestionBatch)
        .order_by(IngestionBatch.ingested_at.desc())
    ).all()
    
    latest_map = {}
    for b in batches:
        # Key by source file? Or by broker?
        # A broker might have multiple files (Holdings + Trans).
        # We assume separate files cover separate things.
        if b.source_file not in latest_map:
            latest_map[b.source_file] = b
            
    return list(latest_map.values())

def get_db_holdings(session):
    """Get current holdings from DB grouped by Broker -> ISIN."""
    holdings = session.scalars(select(Holding)).all()
    data = defaultdict(lambda: defaultdict(float)) # broker -> isin -> qty
    meta = defaultdict(lambda: defaultdict(dict))  # store name/ticker
    
    for h in holdings:
        brk = h.broker.upper() if h.broker else "UNKNOWN"
        isin = normalize_isin(h.isin)
        qty = float(h.quantity)
        data[brk][isin] += qty
        meta[brk][isin] = {'name': h.name, 'ticker': h.ticker}
        
    return data, meta

def run_comparison():
    session = SessionLocal()
    
    print("\n" + "="*80)
    print(f"COMPARISON REPORT (Extraction vs Database) - {datetime.datetime.now()}")
    print("="*80)
    
    # 1. Load DB Snapshot
    db_holdings, db_meta = get_db_holdings(session)
    
    # 2. Load Extracted Data
    batches = get_latest_batches(session)
    
    extracted_holdings = defaultdict(lambda: defaultdict(float))
    extracted_meta = defaultdict(lambda: defaultdict(dict))
    
    print(f"\nAnalyzing {len(batches)} ingestion batches:")
    for b in batches:
        raw = b.raw_data or {}
        h_list = raw.get('holdings', [])
        
        # Only process if it has holdings
        if not h_list:
            continue
            
        print(f"  - [{b.broker}] {b.source_file} ({len(h_list)} items)")
        
        for item in h_list:
            brk = b.broker.upper()
            isin = normalize_isin(item.get('isin'))
            try:
                qty = float(item.get('quantity', 0))
            except:
                qty = 0.0
            
            if isin == "UNKNOWN":
                # Try fallback to ticker
                isin = f"TICKER:{item.get('ticker', 'UNKNOWN')}"
            
            extracted_holdings[brk][isin] += qty
            extracted_meta[brk][isin] = {
                'name': item.get('name'),
                'ticker': item.get('ticker')
            }

    # 3. Compare
    all_brokers = set(db_holdings.keys()) | set(extracted_holdings.keys())
    
    for brk in sorted(all_brokers):
        print(f"\n>>> BROKER: {brk}")
        print(f"{'ISIN/ID':<20} | {'Ticker':<10} | {'DB Qty':<10} | {'Doc Qty':<10} | {'Diff':<10}")
        print("-" * 70)
        
        all_isins = set(db_holdings[brk].keys()) | set(extracted_holdings[brk].keys())
        
        for isin in sorted(all_isins):
            db_q = db_holdings[brk][isin]
            ex_q = extracted_holdings[brk][isin]
            diff = ex_q - db_q
            
            # Lookup metadata
            meta = db_meta[brk][isin] or extracted_meta[brk][isin]
            ticker = meta.get('ticker', '') or ''
            
            if abs(diff) > 0.0001:
                status = f"{diff:+.2f}"
                color_code = "" # ANSI colors could be added
                print(f"{isin[:20]:<20} | {ticker[:10]:<10} | {db_q:<10.2f} | {ex_q:<10.2f} | {status:<10} <--- DIFF")
            else:
                # Match
                 print(f"{isin[:20]:<20} | {ticker[:10]:<10} | {db_q:<10.2f} | {ex_q:<10.2f} | OK")
                 
    session.close()

if __name__ == "__main__":
    run_comparison()
