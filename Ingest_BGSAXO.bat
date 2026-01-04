@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    BGSAXO INGESTION - FRESH START
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo [1/4] Pulizia file JSON intermedi...
if exist orchestration_results.json del orchestration_results.json
if exist extraction_results.json del extraction_results.json
if exist bgsaxo_excel_analysis.md del bgsaxo_excel_analysis.md
echo       ✓ File intermedi rimossi

echo.
echo [2/4] Pulizia DB (Holdings e Transactions BGSAXO)...
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'BGSAXO').delete(); t = s.query(Transaction).filter(Transaction.broker == 'BGSAXO').delete(); s.commit(); print(f'       ✓ Rimossi {h} holdings, {t} transactions'); s.close()"

echo.
echo [3/4] Ingestion dati da Excel...
python scripts/ingest_bgsaxo_v2.py

echo.
echo [4/4] Report finale...
echo.
echo ============================================================
echo    RIEPILOGO BGSAXO
echo ============================================================
python -c "from db.database import SessionLocal; from db.models import Holding, Transaction; from sqlalchemy import func; s = SessionLocal(); h = s.query(Holding).filter(Holding.broker == 'BGSAXO').count(); t = s.query(Transaction).filter(Transaction.broker == 'BGSAXO').count(); print(f'   Holdings:     {h}'); print(f'   Transactions: {t}'); print(); ops = s.query(Transaction.operation, func.count(Transaction.id)).filter(Transaction.broker == 'BGSAXO').group_by(Transaction.operation).all(); print('   Breakdown:'); [print(f'     - {op}: {cnt}') for op, cnt in sorted(ops)]; pnl = s.query(func.sum(Transaction.realized_pnl)).filter(Transaction.broker == 'BGSAXO').scalar(); print(f''); print(f'   Realized P&L: {pnl} EUR'); s.close()"
echo ============================================================

echo.
echo Ingestion BGSAXO completata!
pause
