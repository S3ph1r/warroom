import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

load_dotenv()

def inspect_postgres():
    url = os.getenv("DATABASE_URL", "postgresql://warroom:warroom_dev_password@localhost:5432/warroom_db")
    print(f"\n--- POSTGRESQL INSPECTION ---")
    try:
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = sorted(inspector.get_table_names())
        print(f"Tables found: {tables}")
        
        with engine.connect() as conn:
            for table in tables:
                count = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
                print(f"  [{table}]: {count} rows")
    except Exception as e:
        print(f"Error: {e}")

def inspect_sqlite():
    sqlite_path = project_root / "backend" / "warroom.db"
    print(f"\n--- SQLITE INSPECTION ({sqlite_path.name}) ---")
    if not sqlite_path.exists():
        print("File not found.")
        return
    try:
        engine = create_engine(f"sqlite:///{sqlite_path}")
        inspector = inspect(engine)
        tables = sorted(inspector.get_table_names())
        print(f"Tables found: {tables}")
        with engine.connect() as conn:
            for table in tables:
                count = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
                print(f"  [{table}]: {count} rows")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_postgres()
    print("\n")
    inspect_sqlite()
