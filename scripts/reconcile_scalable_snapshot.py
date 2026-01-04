"""
Reconcile Scalable Snapshot
Parses the latest 'Securities account statement' to true-up holdings.
"""
import sys
import re
import uuid
from pathlib import Path
from decimal import Decimal
from pypdf import PdfReader
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import SessionLocal
from db.models import Holding, Transaction

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def parse_snapshot(pdf_path):
    print(f"Parsing Snapshot: {pdf_path.name}")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        lines = text.split('\n')
        # Structure often: 
        # Qty Name
        # ISIN
        # e.g. "1.0 T esla" / "US88160R1014"
        
        holdings = {} # ISIN -> Qty
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for ISIN
            if re.match(r'^[A-Z]{2}[A-Z0-9]{9}\d$', line):
                isin = line
                # Look backwards for Qty
                # Usually line i-1 or i-2 contains "Qty Name"
                # "1.0 T esla"
                
                # Check i-1
                prev = lines[i-1].strip()
                # Try to extract number at start
                # "10.0 iShares..."
                match = re.match(r'^([\d\.,]+)\s+', prev)
                if match:
                    qty_str = match.group(1).replace(',', '.') # Assume US/Euro fmt mix? dump showed "1.0" or "10.0" (dot decimal?)
                    # Dump showed: "235.22 EUR" (value). Qty is "10.0".
                    # Let's verify number format.
                    try:
                        qty = Decimal(qty_str)
                        holdings[isin] = qty
                        # print(f"  Found: {isin} -> {qty}")
                    except:
                        pass
        return holdings
                        
    except Exception as e:
        print(f"Error parsing snapshot: {e}")
        return {}

def reconcile():
    session = SessionLocal()
    try:
        # Find latest snapshot
        snapshots = list(INBOX.glob("*Securities account statement Broker Scalable Capital*.pdf"))
        if not snapshots:
            print("No snapshot found.")
            return

        snapshots.sort(key=lambda x: x.name)
        latest_snap = snapshots[-1]
        
        real_holdings = parse_snapshot(latest_snap)
        if not real_holdings:
            print("Failed to extract holdings from snapshot.")
            return
            
        print(f"Snapshot contains {len(real_holdings)} positions.")
        
        # Get DB Holdings
        db_holdings = session.query(Holding).filter(Holding.broker == "SCALABLE_CAPITAL").all()
        db_map = {h.isin: h for h in db_holdings}
        
        print("\nReconciling...")
        
        # 1. Check for DB items needing adjustment
        for isin, h in db_map.items():
            db_qty = h.quantity
            real_qty = real_holdings.get(isin, Decimal(0))
            
            diff = real_qty - db_qty
            
            if abs(diff) > Decimal("0.0001"):
                print(f"MISMATCH {h.ticker} ({isin}): DB={db_qty} vs Real={real_qty} -> Diff={diff}")
                
                # Insert Correction Transaction
                tx = Transaction(
                    id=uuid.uuid4(),
                    broker="SCALABLE_CAPITAL",
                    ticker=h.ticker,
                    isin=isin,
                    operation="ADJUSTMENT", # OR 'TRANSFER_OUT' / 'TRANSFER_IN'
                    quantity=abs(diff),
                    price=Decimal(0), # No cash impact
                    total_amount=Decimal(0),
                    currency="EUR", 
                    timestamp=datetime.now(),
                    source_document=f"Reconciled with {latest_snap.name}"
                )
                
                # Correction direction
                if diff < 0:
                     tx.operation = "CORRECTION_DEC" # Decrease
                     h.quantity -= abs(diff)
                else:
                     tx.operation = "CORRECTION_INC" # Increase
                     h.quantity += abs(diff)
                     
                session.add(tx)
                print(f"   -> Corrected DB quantity.")
                
        # 2. Check for Snapshot items missing in DB (New positions?)
        for isin, qty in real_holdings.items():
            if isin not in db_map:
                print(f"MISSING IN DB: {isin} (Qty {qty})")
                # Create Holding
                h = Holding(
                    id=uuid.uuid4(),
                    broker="SCALABLE_CAPITAL",
                    ticker=isin, # Placeholder
                    isin=isin,
                    name=isin,
                    asset_type="STOCK",
                    quantity=qty,
                    purchase_price=Decimal(0),
                    current_value=Decimal(0),
                    currency="EUR",
                    source_document=latest_snap.name,
                    last_updated=datetime.now()
                )
                session.add(h)
                print("   -> Created new holding.")
                
        session.commit()
        print("\n✅ Reconciliation Complete.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    reconcile()
