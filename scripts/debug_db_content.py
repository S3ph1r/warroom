
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv('d:/Download/Progetto WAR ROOM/warroom/.env')
user = os.getenv('POSTGRES_USER', 'postgres')
pwd = os.getenv('POSTGRES_PASSWORD', 'postgres')
db = os.getenv('POSTGRES_DB', 'warroom')
engine = create_engine(f'postgresql://{user}:{pwd}@localhost:5432/{db}')

with engine.connect() as conn:
    print('=== HOLDINGS (Top 5) ===')
    df_h = pd.read_sql("SELECT ticker, name, isin FROM holdings WHERE broker='bgsaxo' LIMIT 5", conn)
    print(df_h.to_string())
    
    print('\n=== TRANSACTIONS (Top 5) ===')
    df_t = pd.read_sql("SELECT ticker, operation, quantity, price, notes FROM transactions WHERE broker='bgsaxo' ORDER BY timestamp DESC LIMIT 5", conn)
    print(df_t.to_string())
