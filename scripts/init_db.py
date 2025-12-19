#!/usr/bin/env python
"""
WAR ROOM - Database Initialization Script
Run this script to create all database tables
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import init_db, engine
from db.models import Base

def main():
    print("🎯 WAR ROOM - Database Initialization")
    print("=" * 50)
    
    try:
        # Test connection
        with engine.connect() as conn:
            print("✅ Connected to PostgreSQL successfully!")
        
        # Create all tables
        print("📦 Creating database tables...")
        init_db()
        
        print("=" * 50)
        print("🚀 Database is ready!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure PostgreSQL is running:")
        print("   docker-compose up -d postgres")
        sys.exit(1)


if __name__ == "__main__":
    main()
