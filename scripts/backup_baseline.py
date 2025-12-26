"""
Backup current Holdings and Transactions to JSON baseline.
Used for comparison after new AI ingestion system runs.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction
from sqlalchemy import select


def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, '__dict__'):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def backup_baseline():
    print("=" * 60)
    print("BACKUP BASELINE DATA")
    print("=" * 60)
    
    # Create baseline directory
    baseline_dir = Path(__file__).parent.parent / "data" / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    session = SessionLocal()
    
    # Export Holdings
    holdings = session.scalars(select(Holding)).all()
    holdings_data = []
    for h in holdings:
        holdings_data.append({
            "id": str(h.id),
            "broker": h.broker,
            "ticker": h.ticker,
            "isin": h.isin,
            "name": h.name,
            "asset_type": h.asset_type,
            "quantity": h.quantity,
            "purchase_price": h.purchase_price,
            "current_value": h.current_value,
            "current_price": h.current_price,
            "currency": h.currency,
            "source_document": h.source_document,
            "last_updated": h.last_updated
        })
    
    holdings_file = baseline_dir / f"holdings_{timestamp}.json"
    with open(holdings_file, 'w', encoding='utf-8') as f:
        json.dump(holdings_data, f, indent=2, default=json_serializer)
    print(f"✅ Exported {len(holdings_data)} holdings → {holdings_file.name}")
    
    # Export Transactions
    transactions = session.scalars(select(Transaction)).all()
    tx_data = []
    for tx in transactions:
        tx_data.append({
            "id": str(tx.id),
            "broker": tx.broker,
            "ticker": tx.ticker,
            "isin": tx.isin,
            "operation": tx.operation,
            "quantity": tx.quantity,
            "price": tx.price,
            "total_amount": tx.total_amount,
            "currency": tx.currency,
            "fees": tx.fees,
            "timestamp": tx.timestamp,
            "source_document": tx.source_document,
            "notes": tx.notes,
            "status": getattr(tx, 'status', 'COMPLETED')
        })
    
    tx_file = baseline_dir / f"transactions_{timestamp}.json"
    with open(tx_file, 'w', encoding='utf-8') as f:
        json.dump(tx_data, f, indent=2, default=json_serializer)
    print(f"✅ Exported {len(tx_data)} transactions → {tx_file.name}")
    
    session.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Holdings: {len(holdings_data)}")
    print(f"Transactions: {len(tx_data)}")
    print(f"Baseline Dir: {baseline_dir}")
    print("=" * 60)
    
    return {
        "holdings_file": str(holdings_file),
        "transactions_file": str(tx_file),
        "holdings_count": len(holdings_data),
        "transactions_count": len(tx_data)
    }


if __name__ == "__main__":
    backup_baseline()
