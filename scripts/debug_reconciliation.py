
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv('d:/Download/Progetto WAR ROOM/warroom/.env')
user = os.getenv('POSTGRES_USER', 'postgres')
pwd = os.getenv('POSTGRES_PASSWORD', 'postgres')
db = os.getenv('POSTGRES_DB', 'warroom')
engine = create_engine(f'postgresql://{user}:{pwd}@localhost:5432/{db}')

with engine.connect() as conn:
    print('=== HOLDINGS (Top 5 with ISIN) ===')
    try:
        df1 = pd.read_sql("SELECT ticker, isin, name FROM holdings WHERE broker='bgsaxo' AND isin IS NOT NULL LIMIT 5", conn)
        print(df1.to_string())
    except: print("No holdings with ISIN found")

    print('\n=== HOLDINGS (Top 5 NO ISIN) ===')
    try:
        df2 = pd.read_sql("SELECT ticker, isin, name FROM holdings WHERE broker='bgsaxo' AND isin IS NULL LIMIT 5", conn)
        print(df2.to_string())
    except: print("No holdings without ISIN found")

    print('\n=== TRANSACTIONS (Top 5) ===')
    try:
        df3 = pd.read_sql("SELECT ticker, isin, operation, notes FROM transactions WHERE broker='bgsaxo' AND operation='BUY' LIMIT 5", conn)
        print(df3.to_string())
    except: print("No transactions found")
