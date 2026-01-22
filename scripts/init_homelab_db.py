#!/usr/bin/env python3
"""
Initialize War Room tables on the homelab shared PostgreSQL database.

Usage:
  From host (Mini PC terminal):  python scripts/init_homelab_db.py --local
  From container:                python scripts/init_homelab_db.py
"""
import os
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

from sqlalchemy import create_engine, text
from db.database import Base
from db.models import (
    Holding, Transaction, ImportLog,
    CouncilSession, PortfolioSnapshot, PriceAlert, IngestionBatch
)

# Database URLs
DB_URL_CONTAINER = "postgresql://homelab:homelab2026@homelab-infra-postgres-1:5432/warroom_db"
DB_URL_LOCAL = "postgresql://homelab:homelab2026@localhost:5432/warroom_db"

def init_homelab_db(use_local: bool = False):
    """Connect to homelab PostgreSQL and create all tables."""
    # Priority: --local flag > LOCAL_DB env > default container URL
    if use_local or os.getenv("LOCAL_DB"):
        db_url = DB_URL_LOCAL
    else:
        db_url = os.getenv("DATABASE_URL", DB_URL_CONTAINER)
    
    print(f"🔌 Connecting to: {db_url.split('@')[1] if '@' in db_url else db_url}")
    
    engine = create_engine(db_url, echo=True)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print(f"✅ Connected: {result.fetchone()[0]}")
    
    print("\n📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        tables = [row[0] for row in result]
        print(f"\n✅ Tables: {', '.join(tables)}")
    
    print("\n🎉 Database initialization complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize War Room DB on homelab")
    parser.add_argument("--local", action="store_true", 
                        help="Use localhost:5432 instead of container hostname")
    args = parser.parse_args()
    init_homelab_db(use_local=args.local)
