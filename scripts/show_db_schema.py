
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
    print('=== HOLDINGS TABLE COLUMNS ===')
    df_h = pd.read_sql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'holdings' ORDER BY ordinal_position", conn)
    print(df_h.to_string(index=False))
    
    print('\n=== TRANSACTIONS TABLE COLUMNS ===')
    df_t = pd.read_sql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'transactions' ORDER BY ordinal_position", conn)
    print(df_t.to_string(index=False))
