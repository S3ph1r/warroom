
import sqlite3
from datetime import datetime

DB_PATH = "backend/warroom.db"

def check_dates():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='council_sessions';")
        if not cursor.fetchone():
            print("Table 'council_sessions' does not exist.")
            return

        cursor.execute("SELECT id, timestamp, consensus_model FROM council_sessions ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} sessions:")
        for r in rows:
            # timestamp might be string or datetime depending on how it was stored/retrieved text affinity
            print(f" - ID: {r[0]} | Date: {r[1]} | Model: {r[2]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dates()
