@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    TRADE REPUBLIC INGESTION - FRESH START
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo [1/3] Pulizia DB (Holdings e Transactions TRADEREPUBLIC)...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'TRADEREPUBLIC').delete(); t = s.query(Transaction).filter(Transaction.broker == 'TRADEREPUBLIC').delete(); s.commit(); print(f'       Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [2/3] Ingestion dati da PDF...
python scripts/ingest_traderepublic_v2.py

echo.
echo [3/3] Report finale...
echo.
echo ============================================================
echo    RIEPILOGO TRADE REPUBLIC
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; from sqlalchemy import func; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'TRADEREPUBLIC').count(); t = s.query(Transaction).filter(Transaction.broker == 'TRADEREPUBLIC').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); ops = s.query(Transaction.operation, func.count(Transaction.id)).filter(Transaction.broker == 'TRADEREPUBLIC').group_by(Transaction.operation).all(); print('   Breakdown:'); [print(f'     - {op}: {cnt}') for op, cnt in sorted(ops)]; s.close()"
echo ============================================================

echo.
echo Ingestion TRADE REPUBLIC completata!
pause
