import os
import sys
import json
from sqlalchemy import func, text
from datetime import date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import CouncilSession

def analyze_db():
    db = SessionLocal()
    try:
        print("--- COUNCIL DB ANALYSIS ---")
        
        # 1. Total Council Sessions
        total_sessions = db.query(CouncilSession).count()
        print(f"Total Sessions: {total_sessions}")
        
        # 2. Total Opinions & Google Opinions
        sessions = db.query(CouncilSession).all()
        total_opinions = 0
        google_opinions = 0
        
        for s in sessions:
            if not s.responses:
                continue
                
            # s.responses is a dict
            responses = s.responses
            total_opinions += len(responses)
            
            for key in responses.keys():
                if "google" in key.lower():
                    google_opinions += 1
                    
        print(f"Total Individual Opinions Stored: {total_opinions}")
        print(f"Total Google Opinions Stored: {google_opinions}")
        
        # 3. President Consensus Count
        consensus_count = db.query(CouncilSession).filter(CouncilSession.consensus.isnot(None)).count()
        print(f"Total Consensus Records: {consensus_count}")
        
        # 4. Sessions per Day per Model
        # Group by date and consensus_model
        sql = text("""
            SELECT 
                DATE(timestamp) as session_date, 
                consensus_model, 
                COUNT(*) as count 
            FROM council_sessions 
            GROUP BY session_date, consensus_model 
            ORDER BY session_date DESC
        """)
        
        result = db.execute(sql).fetchall()
        
        print("\n--- SESSIONS PER DAY (By Consensus Model) ---")
        for row in result:
             print(f"Date: {row[0]} | Model: {row[1]} | Count: {row[2]}")

    except Exception as e:
        print(f"Error analyzing DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    analyze_db()
