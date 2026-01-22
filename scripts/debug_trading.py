
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
    print('=== TRADING TRANSACTIONS (Top 5) ===')
    df_t = pd.read_sql("SELECT ticker, operation, quantity, price, notes FROM transactions WHERE operation='BUY' LIMIT 5", conn)
    print(df_t.to_string())
