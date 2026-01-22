"""
Reconciliation Script: BG Saxo (Holdings vs Transactions)
=========================================================
Verifies that Current Holdings match the sum of Historical Transactions.
Matches primarily by ISIN.
"""
import sys
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Holding, Transaction

def normalize_isin(isin):
    if not isin: return "UNKNOWN"
    return isin.strip().upper()

def main():
    session = SessionLocal()
    print("Loading data...")
    
    # 1. Load Holdings
    holdings = session.query(Holding).filter(Holding.broker == 'BG_SAXO').all()
    holdings_map = {normalize_isin(h.isin): h for h in holdings}
    print(f"Loaded {len(holdings)} holdings.")
    
    # 2. Load Transactions
    transactions = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').all()
    print(f"Loaded {len(transactions)} transactions.")
    
    # 3. Calculate Theoretical Positions
    theory_positions = defaultdict(Decimal)
    
    for t in transactions:
        isin = normalize_isin(t.isin)
        qty = t.quantity
        op = t.operation
        
        # Sign Logic Handling
        # If the parser extracted negative quantity for Sells, simple sum works.
        # If it extracted positive quantity for Sells, we must flip.
        # Inspecting logic: 'Vendi-145' -> -145. 'Acquista100' -> 100.
        # But 'Vendi 100' -> ?
        # Let's enforce logical signs based on Operation if specific Ops are present.
        
        if op == 'SELL' and qty > 0:
            qty = -qty
        elif op == 'BUY' and qty < 0:
            qty = abs(qty) # Should include positive
            
        # Transfers: 
        # DEPOSIT -> + 
        # WITHDRAW -> -
        # If operation is just 'TRANSFER' or 'TRADE' (generic), rely on sign.
        
        theory_positions[isin] += qty

    # 4. Compare
    with open('reconciliation_report.txt', 'w', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"{'ISIN':<15} | {'TICKER (Hold)':<20} | {'ACTUAL':>10} | {'THEORY':>10} | {'DELTA':>10} | {'STATUS':<5}\n")
        f.write("="*80 + "\n")
        
        matches = 0
        mismatches = 0
        
        all_isins = set(holdings_map.keys()) | set(theory_positions.keys())
        
        for isin in sorted(all_isins):
            if isin == "UNKNOWN": continue
            
            # Actual
            actual_qty = Decimal(0)
            h_ticker = "-"
            if isin in holdings_map:
                actual_qty = holdings_map[isin].quantity
                h_ticker = holdings_map[isin].ticker
                
            # Theory
            theory_qty = theory_positions.get(isin, Decimal(0))
            
            delta = actual_qty - theory_qty
            
            # Status
            if abs(delta) < Decimal("0.0001"):
                status = "✅"
                matches += 1
            else:
                status = "❌"
                mismatches += 1
                
            # Filter output: always show mismatches, but skip closed positions (0 vs 0)
            # Should we show active matches? Yes, for confirmation.
            if abs(actual_qty) < 0.0001 and abs(theory_qty) < 0.0001:
                continue
                
            f.write(f"{isin:<15} | {h_ticker[:20]:<20} | {actual_qty:>10.4f} | {theory_qty:>10.4f} | {delta:>10.4f} | {status}\n")

        f.write("="*80 + "\n")
        f.write(f"MATCHES: {matches}\n")
        f.write(f"MISMATCHES: {mismatches}\n")
        
    print("Report written to reconciliation_report.txt")
    
    session.close()

if __name__ == "__main__":
    main()
