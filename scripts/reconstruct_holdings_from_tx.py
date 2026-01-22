import sys
import logging
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal, init_db
from db.models import Holding, Transaction
from services.price_service_v5 import resolve_asset_info

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("Holdings_Reconstructor")

def reconstruct_holdings(broker_name):
    print("\n" + "="*60)
    print(f" 🏗️  RECONSTRUCTING HOLDINGS FROM TRANSACTIONS: {broker_name}")
    print("="*60)
    
    print("\n> [!WARNING]")
    print("> Questa procedura ricostruisce le posizioni attuali aggregando tutti i movimenti nel DB.")
    print("> FUNZIONA SOLO se hai caricato TUTTA la cronologia dal giorno dell'apertura del conto.")
    print("> Se mancano periodi intermedi o precedenti, le quantità calcolate saranno PARZIALI.\n")

    init_db()
    session = SessionLocal()
    
    try:
        # 1. Fetch all transactions for this broker, sorted by timestamp
        txns = session.query(Transaction).filter(Transaction.broker == broker_name).order_by(Transaction.timestamp).all()
        
        if not txns:
            logger.warning(f"   ❌ No transactions found for broker {broker_name}.")
            return

        logger.info(f"   📊 Found {len(txns)} transactions. Aggregating quantities...")

        # 2. Aggregate quantities and calculate WAC
        # Key: (isin or ticker or name)
        # positions[asset_key] = {"qty": Decimal, "avg": Decimal, "isin": str}
        positions = defaultdict(lambda: {"qty": Decimal(0), "avg": Decimal(0), "isin": None})
        
        for tx in txns:
            op = tx.operation.upper()
            qty = tx.quantity
            
            # Identify the asset (prefer ISIN, then Ticker)
            asset_key = tx.isin or tx.ticker
            if not asset_key or asset_key == "UNKNOWN":
                continue
                
            if tx.isin: positions[asset_key]["isin"] = tx.isin
            # Note: We don't have a name in the Transaction model! 
            # We'll need to join or keep it simple.
            
            if op == "BUY":
                new_qty = positions[asset_key]["qty"] + qty
                if new_qty > 0:
                    positions[asset_key]["avg"] = ((positions[asset_key]["qty"] * positions[asset_key]["avg"]) + (qty * tx.price)) / new_qty
                positions[asset_key]["qty"] = new_qty
            elif op == "SELL":
                positions[asset_key]["qty"] -= qty
                # Avg basis doesn't change on SELL 

        # 3. Update holdings table
        logger.info("   📥 Updating 'holdings' table...")
        
        # Clear existing holdings for this broker to prevent duplicates
        session.query(Holding).filter(Holding.broker == broker_name).delete()
        
        count = 0
        for key, data in positions.items():
            if data["qty"] <= 0:
                continue # Skip closed positions
            
            # Resolve real ticker and name from ISIN/Key
            info = resolve_asset_info(data["isin"], key)
            
            h = Holding(
                broker=broker_name,
                ticker=info['ticker'],
                isin=data["isin"],
                name=info['name'],
                quantity=data["qty"],
                purchase_price=data["avg"],
                current_price=Decimal(0),
                current_value=Decimal(0),
                asset_type="STOCK", # Default
                notes="Reconstructed from transactions history."
            )
            session.add(h)
            count += 1
            logger.info(f"      ✅ {info['ticker']} ({info['name']}): {data['qty']} units")

        session.commit()
        print(f"\n✅ RECONSTRUCTION COMPLETE: {count} active positions created.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"   ❌ Reconstruction failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    broker = "TRADE_REPUBLIC"
    if len(sys.argv) > 1:
        broker = sys.argv[1]
    
    reconstruct_holdings(broker)
