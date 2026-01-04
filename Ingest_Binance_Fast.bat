@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    BINANCE FAST INGESTION (CSV Only)
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo [1/3] Pulizia DB (Holdings e Transactions BINANCE)...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'BINANCE').delete(); t = s.query(Transaction).filter(Transaction.broker == 'BINANCE').delete(); s.commit(); print(f'       Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [2/3] Ingestion Rapida da CSV (Full History 2017-2026)...
python scripts/ingest_binance_v2.py

echo.
echo [3/3] Report finale...
echo.
echo ============================================================
echo    RIEPILOGO BINANCE
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; from sqlalchemy import func; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'BINANCE').count(); t = s.query(Transaction).filter(Transaction.broker == 'BINANCE').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); s.close()"
echo ============================================================
echo.
echo NOTA: I prezzi storici sono a 0. Esegui 'Enrich_Binance_Prices.bat' per scaricarli.
echo.
echo Ingestion BINANCE completata!
pause
