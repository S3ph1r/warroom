
from sqlalchemy import create_engine
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv('d:/Download/Progetto WAR ROOM/warroom/.env')
user = os.getenv('POSTGRES_USER', 'postgres')
pwd = os.getenv('POSTGRES_PASSWORD', 'postgres')
db = os.getenv('POSTGRES_DB', 'warroom')
engine = create_engine(f'postgresql://{user}:{pwd}@localhost:5432/{db}')

with engine.connect() as conn:
    print('=== HOLDINGS (Check for ISIN) ===')
    df1 = pd.read_sql("SELECT ticker, isin, name, quantity FROM holdings WHERE broker='bgsaxo' LIMIT 5", conn)
    print(df1.to_string())
    
    print('\n=== TRANSACTIONS (Check for Ticker/ISIN) ===')
    df2 = pd.read_sql("SELECT ticker, isin, operation, quantity, notes FROM transactions WHERE broker='bgsaxo' AND operation='BUY' LIMIT 5", conn)
    print(df2.to_string())
    
    print('\n=== TOTAL COUNTS ===')
    h_count = pd.read_sql("SELECT count(*) FROM holdings WHERE broker='bgsaxo'", conn).iloc[0,0]
    t_count = pd.read_sql("SELECT count(*) FROM transactions WHERE broker='bgsaxo'", conn).iloc[0,0]
    print(f"Holdings: {h_count}, Transactions: {t_count}")
