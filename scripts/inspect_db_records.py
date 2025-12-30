
import sys
from pathlib import Path
import json
from decimal import Decimal
from datetime import datetime

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, Holding
from sqlalchemy import inspect

def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

def json_serial(obj):
    if isinstance(obj, (datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError (f"Type {type(obj)} not serializable")

import uuid

def main():
    session = SessionLocal()
    with open('db_inspection.txt', 'w', encoding='utf-8') as f:
        f.write("--- SAMPLE TRANSACTION RECORD ---\n")
        tx = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').first()
        if tx:
            data = to_dict(tx)
            max_key_len = max(len(k) for k in data.keys())
            for k, v in data.items():
                f.write(f"{k.ljust(max_key_len)} : {v}\n")
        else:
            f.write("No transactions found.\n")

        f.write("\n--- SAMPLE HOLDING RECORD ---\n")
        h = session.query(Holding).filter(Holding.broker == 'BG_SAXO').first()
        if h:
            data = to_dict(h)
            max_key_len = max(len(k) for k in data.keys())
            for k, v in data.items():
                f.write(f"{k.ljust(max_key_len)} : {v}\n")
        else:
            f.write("No holdings found.\n")
        
    session.close()
    print("Inspection written to db_inspection.txt")

if __name__ == "__main__":
    main()
