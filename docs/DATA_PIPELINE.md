# 🛠️ Data Pipeline & Dashboard Logic

This document describes the end-to-end data flow for the War Room dashboard, including ingestion, price fetching, and P/L calculations.

## 1. 📥 Ingestion Layer (Universal System 2.0)

The new **Universal Ingestion System** consolidates data from all 5 brokers into a normalized database structure, enabling accurate P&L tracking and historical reconciliation.

### Data Flow
1.  **Source Documents**: PDFs (Revolut, Trade Republic, Scalable), CSVs (Binance, Scalable, Saxo), or Excel.
2.  **Extraction**: 
    - **Mistral LLM**: Used for complex/unstructured PDFs (e.g., Revolut Statements, Trade Republic Notes).
    - **Deterministic Parsers**: Used for structured CSVs (Binance, Saxo).
3.  **Normalization**: All transactions are converted to a standard JSON format (`date`, `type`, `asset`, `quantity`, `amount`) and saved in `scripts/`.
4.  **Ingestion (`ingest_all_to_db.py`)**:
    - Truncates existing `transactions` and `holdings` tables.
    - Loads verified JSON files (`bgsaxo_transactions_full.json`, `scalable_transactions_full.json`, `revolut_full_reconciled.json`, `tr_final.json`, `binance_final.json`).
    - **Reconciles History**: Rebuilds current holdings by aggregating entire transaction history (Buy/Sell/Split).
    - **Single Source of Truth**: The Database is the final authority.

### Brokers & Parsers

| Broker | Parser Strategy | Status |
|--------|-----------------|--------|
| **BG Saxo** | Hybrid (LLM Discovery + Regex Block Parsing) | ✅ Full History (Reconciled) |
| **Trade Republic** | PDF (Estratto Conto) -> JSON (Mistral) | ✅ Verified (Partial History Sep 24 on) |
| **Scalable** | PDF/CSV -> JSON (Universal Parser) | ✅ Full History |
| **Revolut** | PDF (Statement) -> JSON (Mistral) | ✅ Stocks & Crypto Reconciled |
| **Binance** | CSV -> JSON (Deterministic) | ✅ Full History (2000+ Txns) |

### Manual Corrections
Since the core logic is "History-Based", any missing history (e.g. pre-2024 Trade Republic) results in negative balances.
**Fix:** Use the Dashboard's **"New Transaction"** button to insert `DEPOSIT` or `BUY` operations to correct the starting balance.
**Note:** A "Reset DB" will wipe these manual corrections unless they are backed up to the JSON source files.

---

## 2. 💹 Price Service v5 (`services/price_service_v5.py`)

The heart of the system. It fetches live prices with a **cascading fallback strategy**.

### Strategy Order
1.  **Fixed Cash**: EUR = 1, USD = 0.853 (configurable).
2.  **Commodities**: Gold (XAU) and Silver (XAG) use fixed rates calibrated to Revolut (configurable).
3.  **Crypto (CoinGecko)**: Fetches live prices for BTC, ETH, etc.
4.  **Stocks/ETFs (Yahoo Finance)**:
    *   **ISIN Lookup**: Uses OpenFIGI to find the best ticker for the ISIN.
    *   **Exchange Logic**: Prioritizes `.MI` (Milan), `.DE` (Xetra), `.L` (London) based on ISIN prefix (IE/LU/IT/DE).
    *   **Ticker Lookup**: Fallback to raw ticker if ISIN fails.
5.  **Alpha Vantage**: Secondary backup for US stocks.
6.  **DB Fallback**: If everything runs dry, returns `purchase_price` from DB (Flagged as non-live).

### 🌍 Currency Handling
*   All prices are converted to **EUR** before returning.
*   Yahoo Finance prices are converted using real-time FX rates (or hardcoded fallbacks if API fails).
*   **GBp (Pence)**: Automatically detected and divided by 100 to get GBP.

---

## 3. 📊 Dashboard Layer (v5 - Svelte & FastAPI)

The dashboard now follows a modern decoupled architecture.

### Data Flow
1. **Frontend (Svelte)**: Polls `/api/portfolio` from the FastAPI backend.
2. **Backend (FastAPI)**: 
    - Fetches holdings from DB.
    - Calls `PriceService` for real-time prices and **Daily P&L**.
    - Aggregates data by **Broker** and **Asset Type**.
    - Calculates global KPIs (Total value, Net P&L%, Day P&L%).
3. **Frontend Rendering**:
    - **AssetTable.svelte**: Dedicated component for the 6-tile layout.
    - **Reactive Filtering**: Svelte reactive statements ($:) filter data by `selectedBroker` without new API calls.
    - **Sorting**: Client-side sorting on all columns (Ticker, Value, P&L, etc.).

### Day P&L Logic
The `price_service_v5.py` fetches the **previous close** for all assets (Stocks/ETFs via Yahoo, Crypto via CoinGecko).
- `day_change_pct` = ((Live Price - Prev Close) / Prev Close) * 100
- `day_pl` = (Live Price - Prev Close) * Quantity

### Caching
- **Backend Memory Cache**: `PriceService` caches prices for 1 hour.
- **Frontend State**: Svelte stores the portfolio data in local variables until manual refresh.

---

## 4. 🧰 Debugging Tools

Scripts available in `scripts/`:
*   `compare_detail.py`: Compares Dashboard values vs User App values line-by-line.
*   `debug_conversion.py`: Verifies FX conversion for specific assets (e.g., NOVOB DKK->EUR).
*   `insert_binance.py`: Helper to reset Binance holdings.
*   `analyze_pnl.py`: Lists top winners/losers to spot data anomalies.

## 5. ⚠️ Known Issues
*   **Revolut Cost Basis**: Revolut exports often lack original cost basis, so P/L may be near 0 for some assets.
*   **Delisted Assets**: Old assets (e.g., Russian ETFs) may fail to fetch prices and default to DB values.
