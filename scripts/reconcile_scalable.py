from db.database import SessionLocal
from db.models import Transaction, Holding
from decimal import Decimal

def run_reconciliation():
    s = SessionLocal()
    broker = 'SCALABLE_CAPITAL'
    txs = s.query(Transaction).filter(Transaction.broker == broker).all()
    holds = s.query(Holding).filter(Holding.broker == broker).all()
    
    print(f"{'Ticker':<25} | {'ISIN':<15} | {'In DB':>10} | {'Calculated':>10} | {'Diff':>10} | {'Txs':>5}")
    print("-" * 85)
    
    for h in sorted(holds, key=lambda x: x.ticker):
        # Match by ISIN
        assets_txs = [t for t in txs if t.isin == h.isin]
        buy_sum = sum(t.quantity for t in assets_txs if t.operation == 'BUY')
        sell_sum = sum(t.quantity for t in assets_txs if t.operation == 'SELL')
        calc_qty = buy_sum - sell_sum
        diff = h.quantity - calc_qty
        
        print(f"{h.ticker:<25} | {h.isin:<15} | {h.quantity:>10.2f} | {calc_qty:>10.2f} | {diff:>10.2f} | {len(assets_txs):>5}")
    
    s.close()

if __name__ == "__main__":
    run_reconciliation()
