from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def show_all_holdings():
    db = SessionLocal()
    holdings = db.query(Holding).all()
    
    if not holdings:
        print("No holdings found in database.")
        db.close()
        return

    data = []
    for h in holdings:
        data.append({
            "Broker": h.broker,
            "Ticker": h.ticker,
            "Name": h.name,
            "Type": h.asset_type,
            "Qty": float(h.quantity),
            "AvgPrice": float(h.purchase_price) if h.purchase_price else 0.0,
            "Value (EUR)": float(h.current_value),
            "Currency": h.currency
        })
    
    db.close()
    
    df = pd.DataFrame(data)
    # Sort by Broker, then Value desc
    df = df.sort_values(by=["Broker", "Value (EUR)"], ascending=[True, False])
    
    print(f"\n=== ALL HOLDINGS ({len(df)}) ===")
    print(df.to_string(index=False))
    print(f"\nTOTAL PORTFOLIO VALUE: €{df['Value (EUR)'].sum():,.2f}")

if __name__ == "__main__":
    show_all_holdings()
