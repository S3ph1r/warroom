@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    REVOLUT INGESTION - FRESH START
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo [1/3] Pulizia DB (Holdings e Transactions REVOLUT)...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'REVOLUT').delete(); t = s.query(Transaction).filter(Transaction.broker == 'REVOLUT').delete(); s.commit(); print(f'       Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [2/3] Ingestion dati da Excel + PDF...
python scripts/ingest_revolut_v2.py

echo.
echo [3/3] Report finale...
echo.
echo ============================================================
echo    RIEPILOGO REVOLUT
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; from sqlalchemy import func; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'REVOLUT').count(); t = s.query(Transaction).filter(Transaction.broker == 'REVOLUT').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); types = s.query(Holding.asset_type, func.count(Holding.id)).filter(Holding.broker == 'REVOLUT').group_by(Holding.asset_type).all(); print('   Holdings by type:'); [print(f'     - {t}: {c}') for t, c in types]; s.close()"
echo ============================================================

echo.
echo Ingestion REVOLUT completata!
pause
