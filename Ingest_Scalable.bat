@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    SCALABLE CAPITAL INGESTION (Full History)
echo ============================================================
echo.

cd /d %~dp0
echo.
echo Cartella di lavoro: %CD%
set PYTHONPATH=.

echo [1/3] Pulizia dati Scalable Capital precedenti...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'SCALABLE_CAPITAL').delete(); t = s.query(Transaction).filter(Transaction.broker == 'SCALABLE_CAPITAL').delete(); s.commit(); print(f'       Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [2/3] Esecuzione Ingestion (Monthly Statements)...
python scripts/ingest_scalable_v2.py

echo.
echo [3/3] Report finale...
echo ============================================================
echo    RIEPILOGO SCALABLE
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'SCALABLE_CAPITAL').count(); t = s.query(Transaction).filter(Transaction.broker == 'SCALABLE_CAPITAL').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); s.close()"
echo ============================================================
echo.
echo [4/4] Pulizia Cache Dashboard...
if exist "data\portfolio_snapshot.json" (
    del "data\portfolio_snapshot.json"
    echo    - Snapshot cancellato: Refresh Dashboard forzato.
) else (
    echo    - Nessun snapshot da cancellare.
)

echo.
echo Ingestion Completata!
pause
