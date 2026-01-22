"""
Transaction Ticker Normalizer

Normalizes transaction tickers to match Holdings table format.
Uses Holdings as the canonical source of truth.

Matching Strategy:
1. ISIN match (most reliable)
2. Case-insensitive ticker match
3. Fuzzy name matching (for LLM-extracted names)
"""

import sys
from pathlib import Path
from difflib import SequenceMatcher

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.database import SessionLocal
from db.models import Holding, Transaction
from collections import defaultdict


def similarity(a, b):
    """Calculate string similarity ratio (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_name(name):
    """Remove common suffixes and normalize a stock name."""
    if not name:
        return ""
    n = name.upper().strip()
    # Remove common suffixes
    for suffix in [' INC.', ' INC', ' CORP.', ' CORP', ' LTD.', ' LTD', ' A/S', ' NV', 
                   ' SA', ' AG', ' PLC', ' ADR', ' - ADR', ' STOCK', ' ETF']:
        n = n.replace(suffix, '')
    # Remove punctuation
    n = ''.join(c for c in n if c.isalnum() or c == ' ')
    return n.strip()


def build_holdings_index(holdings):
    """Build lookup indexes from holdings."""
    by_ticker_lower = {}
    by_isin = {}
    by_name_normalized = {}
    
    for h in holdings:
        ticker = h.ticker.lower() if h.ticker else ""
        isin = h.isin.upper() if h.isin else ""
        name = normalize_name(h.name)
        
        if ticker:
            by_ticker_lower[ticker] = h.ticker
            # Also add just the symbol part (before :)
            if ':' in ticker:
                symbol = ticker.split(':')[0]
                by_ticker_lower[symbol] = h.ticker
                by_ticker_lower[symbol.upper()] = h.ticker
        
        if isin:
            by_isin[isin] = h.ticker
            
        if name:
            by_name_normalized[name] = h.ticker
    
    return by_ticker_lower, by_isin, by_name_normalized


def find_canonical_ticker(txn, ticker_index, isin_index, name_index, holdings):
    """Try to find the canonical ticker for a transaction."""
    original = txn.ticker
    
    # 1. Try exact case-insensitive ticker match
    if original.lower() in ticker_index:
        return ticker_index[original.lower()], "ticker_exact"
    
    # 2. Try symbol-only match (NVDA from NVDA:XNAS)
    if ':' in original:
        symbol = original.split(':')[0].lower()
        if symbol in ticker_index:
            return ticker_index[symbol], "symbol_match"
    
    # 3. Try ISIN match
    if txn.isin:
        isin = txn.isin.upper()
        if isin in isin_index:
            return isin_index[isin], "isin_match"
    
    # 4. Try name normalization + exact match
    norm_name = normalize_name(original)
    if norm_name in name_index:
        return name_index[norm_name], "name_exact"
    
    # 5. Try fuzzy name matching
    best_match = None
    best_score = 0
    for h in holdings:
        h_name = normalize_name(h.name)
        score = similarity(norm_name, h_name)
        if score > best_score and score > 0.7:  # 70% threshold
            best_score = score
            best_match = h.ticker
    
    if best_match:
        return best_match, f"fuzzy_{int(best_score*100)}%"
    
    return None, "no_match"


def normalize_transactions(broker, dry_run=True):
    """Normalize all transactions for a broker."""
    db = SessionLocal()
    
    try:
        # Get holdings
        holdings = db.query(Holding).filter(Holding.broker == broker).all()
        print(f"📦 Holdings for {broker}: {len(holdings)}")
        
        # Build indexes
        ticker_index, isin_index, name_index = build_holdings_index(holdings)
        print(f"   Ticker Index: {len(ticker_index)} entries")
        print(f"   ISIN Index: {len(isin_index)} entries")
        print(f"   Name Index: {len(name_index)} entries")
        print()
        
        # Get transactions
        txns = db.query(Transaction).filter(Transaction.broker == broker).all()
        print(f"📝 Transactions: {len(txns)}")
        
        # Track changes
        changes = []
        no_match = []
        already_ok = []
        
        for txn in txns:
            canonical, method = find_canonical_ticker(
                txn, ticker_index, isin_index, name_index, holdings
            )
            
            if canonical:
                if txn.ticker.lower() == canonical.lower():
                    already_ok.append(txn.ticker)
                else:
                    changes.append({
                        'id': txn.id,
                        'old': txn.ticker,
                        'new': canonical,
                        'method': method
                    })
                    if not dry_run:
                        txn.ticker = canonical
            else:
                no_match.append(txn.ticker)
        
        # Report
        print()
        print("=" * 60)
        print("📊 NORMALIZATION RESULTS")
        print("=" * 60)
        print(f"✅ Already correct: {len(already_ok)}")
        print(f"🔄 To update: {len(changes)}")
        print(f"❌ No match found: {len(no_match)}")
        print()
        
        # Show sample changes
        if changes:
            print("🔄 Sample Changes (first 20):")
            for c in changes[:20]:
                print(f"   {c['old'][:25]:<25} → {c['new']:<15} ({c['method']})")
        
        if no_match:
            print()
            print("❌ Unmatched (first 20):")
            unique_unmatched = list(set(no_match))[:20]
            for u in unique_unmatched:
                print(f"   {u}")
        
        if not dry_run and changes:
            db.commit()
            print()
            print(f"✅ COMMITTED {len(changes)} changes to database!")
        elif changes:
            print()
            print("⚠️ DRY RUN - No changes made. Set dry_run=False to apply.")
        
        return changes, no_match
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="bgsaxo")
    parser.add_argument("--apply", action="store_true", help="Apply changes (not dry run)")
    args = parser.parse_args()
    
    normalize_transactions(args.broker, dry_run=not args.apply)
