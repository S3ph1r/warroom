@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo    BINANCE PRICE ENRICHMENT
echo ============================================================
echo.

cd /d "D:\Download\Progetto WAR ROOM\warroom"
set PYTHONPATH=.

echo Avvio arricchimento prezzi storici...
echo (Questo processo puo richiedere molto tempo: ~600 richieste al minuto)
echo.

echo [1/2] Fetch Prezzi da API Binance...
python scripts/enrich_binance_prices.py

echo.
echo [2/2] Ricalcolo Costo Medio Ponderato (WAC)...
python scripts/recalc_binance_holdings.py

echo.
echo ============================================================
echo   ARRICCHIMENTO COMPLETATO!
echo ============================================================
echo   I tuoi prezzi di carico (Purchase Price) sono aggiornati.
pause
