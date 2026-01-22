"""
Inspect DB Schema (Standalone)
"""
import os
import sys
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv
from pathlib import Path

def get_db_url_inline():
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "warroom")
    return f"postgresql://{user}:{password}@{server}:{port}/{db}"

url = get_db_url_inline()
engine = create_engine(url)

inspector = inspect(engine)
columns = inspector.get_columns('transactions')

print("📊 TABLE: transactions")
for c in columns:
    length = c['type'].length if hasattr(c['type'], 'length') else 'N/A'
    print(f"- {c['name']} ({c['type']}) [Max Len: {length}]")
