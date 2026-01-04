@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==============================================================================
echo    WAR ROOM - UPDATE ALL PORTFOLIOS
echo ==============================================================================
echo.
echo    This script will update all broker data:
echo    1. REVOLUT (Transazioni + Crypto Holdings)
echo    2. BG SAXO (Excel Reports)
echo    3. TRADE REPUBLIC (PDF Statement)
echo    4. BINANCE (CSV + Price Enhancement)
echo    5. IBKR (CSV History)
echo    6. SCALABLE CAPITAL (Monthly PDFs)
echo.
echo    [NOTA] I prezzi storici di Binance richiedono tempo (Enrichment).
echo    Se vuoi aggiornarli, usa 'Enrich_Binance_Prices.bat' separatamente.
echo.
pause

echo.
echo [1/6] Aggiornamento REVOLUT...
call Ingest_Revolut.bat /NOPAUSE

echo.
echo [2/6] Aggiornamento BG SAXO...
call Ingest_BGSAXO.bat /NOPAUSE

echo.
echo [3/6] Aggiornamento TRADE REPUBLIC...
call Ingest_TradeRepublic.bat /NOPAUSE

echo.
echo [4/6] Aggiornamento BINANCE (Fast)...
call Ingest_Binance_Fast.bat /NOPAUSE

echo.
echo [5/6] Aggiornamento IBKR...
call Ingest_IBKR.bat /NOPAUSE

echo.
echo [6/6] Aggiornamento SCALABLE CAPITAL...
call Ingest_Scalable.bat /NOPAUSE

echo.
echo ==============================================================================
echo    TUTTI I PORTAFOGLI AGGIORNATI!
echo ==============================================================================
echo.
echo    Totale Holdings e Transazioni sono ora sincronizzate nel Database.
echo    Apri la Dashboard per vedere i grafici.
echo.
pause
