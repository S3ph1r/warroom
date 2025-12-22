
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.database import DATABASE_URL, Base
from db.models import CouncilSession

def check_db():
    print("🔎 Checking Council DB storage...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    count = session.query(CouncilSession).count()
    print(f"📊 Total Council Sessions found: {count}")
    
    if count > 0:
        last = session.query(CouncilSession).order_by(CouncilSession.timestamp.desc()).first()
        print(f"   Last Session: {last.timestamp}")
        print(f"   Context Keys: {last.context_snapshot.keys()}")
        print(f"   Responses: {len(last.responses)} advisors")
    else:
        print("❌ No sessions found.")

if __name__ == "__main__":
    check_db()
