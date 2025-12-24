
import sys
import os
from pathlib import Path

# Setup Path to import from warroom modules
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import DB and Models
from db.database import SessionLocal
from db.models import CouncilSession
from sqlalchemy import func, cast, Date

def check_dates():
    try:
        db = SessionLocal()
        # Query distinct dates
        sessions = db.query(CouncilSession.timestamp, CouncilSession.consensus_model, CouncilSession.id).order_by(CouncilSession.timestamp.desc()).all()
        
        print(f"Found {len(sessions)} sessions in PostgreSQL:")
        for s in sessions:
            print(f" - ID: {s.id} | Date: {s.timestamp} | Model: {s.consensus_model}")
            
        if len(sessions) == 0:
            print("No sessions found.")
            
        db.close()
    except Exception as e:
        print(f"Error connecting/querying: {e}")

if __name__ == "__main__":
    check_dates()
