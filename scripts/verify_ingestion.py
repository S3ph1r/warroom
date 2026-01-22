
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Holding, Transaction

def verify():
    s = SessionLocal()
    h_count = s.query(Holding).filter(Holding.broker == "BG_SAXO").count()
    t_count = s.query(Transaction).filter(Transaction.broker == "BG_SAXO").count()
    s.close()
    
    print(f"VERIFICATION RESULT:")
    print(f"Holdings: {h_count}")
    print(f"Transactions: {t_count}")
    
    print(f"Transactions: {t_count}")
    
    # Try inserting dummy
    import uuid
    from datetime import datetime
    try:
        dummy = Transaction(
            id=uuid.uuid4(),
            broker="TEST_BROKER",
            ticker="TEST",
            operation="BUY",
            status="COMPLETED",
            quantity=1,
            price=10.0,
            total_amount=10.0,
            timestamp=datetime.now(),
            source_document="manual_test"
        )
        s.add(dummy)
        s.commit()
        print("✅ Dummy Insert SUCCESS")
        # Cleanup
        s.delete(dummy)
        s.commit()
    except Exception as e:
        print(f"❌ Dummy Insert FAILED: {e}")
        s.rollback()

    if h_count > 0: # Transaction count might be 0 until fixed
        print("✅ HOLDINGS SUCCESS")
    else:
        print("❌ HOLDINGS FAILURE")

if __name__ == "__main__":
    verify()
