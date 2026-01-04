@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    IBKR INGESTION (CSV Only - Full History)
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo [1/3] Pulizia dati IBKR precedenti...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'IBKR').delete(); t = s.query(Transaction).filter(Transaction.broker == 'IBKR').delete(); s.commit(); print(f'       Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [2/3] Esecuzione Ingestion...
python scripts/ingest_ibkr_v2.py

echo.
echo [3/3] Report finale...
echo ============================================================
echo    RIEPILOGO IBKR
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'IBKR').count(); t = s.query(Transaction).filter(Transaction.broker == 'IBKR').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); s.close()"
echo ============================================================
echo.
echo Ingestion IBKR completata!
pause
