# 🛠️ Data Pipeline & Dashboard Logic

This document describes the end-to-end data flow for the War Room dashboard, including ingestion, price fetching, and P/L calculations.

## 1. 📥 Ingestion Layer

The ingestion process reads broker documents from `G:\Il mio Drive\WAR_ROOM_DATA\inbox` and inserts them into the `holdings` database table.

### Brokers & Parsers

| Broker | Parser File | Logic |
|--------|-------------|-------|
| **BG Saxo** | `bgsaxo_transactions.py` | Calculates holdings from Excel transaction history (Buy/Sell/Split/Merger). Calculates weighted average cost. |
| **Trade Republic** | `trade_republic.py` | Reads current positions directly from CSV export. Includes purchase price. |
| **Scalable** | `scalable_capital.py` | Reads current positions from WUM CSV. Includes purchase price. |
| **IBKR** | `ibkr.py` | Reads positions from XML Flex Query. Cost basis available. |
| **Revolut** | `revolut.py` | Reads holdings from CSV statement. **Limitation**: Does not provide historical cost, so P/L is relative to current period or 0. |
| **Binance** | `insert_binance.py` | **Manual Ingestion** (temporary). Inserts SPOT+EARN holdings from user-provided data. |

### Data Schema (`holdings` table)
- `ticker`: Asset symbol (e.g., AAPL)
- `isin`: Unique ID (e.g., US0378331005)
- `quantity`: Number of shares/units
- `purchase_price`: Cost per unit (in native `currency`)
- `currency`: Currency of the asset (USD, EUR, DKK, etc.)
- `broker`: Source broker name

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

## 3. 📊 Dashboard & P/L Calculation (`dashboard/app.py`)

The dashboard displays the data using the following logic:

### P/L Formula
```python
Live Value (EUR)    = Quantity × Live Price (EUR)
Cost Basis (EUR)    = Quantity × Purchase Price (Native) × FX_Rate(Native->EUR)
P/L (EUR)           = Live Value - Cost Basis
P/L %               = (P/L / Cost Basis) * 100
```
> **Note**: The `FX_Rate` is critical. If ignored, comparing `USD Cost` vs `EUR Value` leads to massive fake losses.

### Caching
*   **Streamlit Cache**: `st.cache_data` stores loaded holdings.
*   **Price Service Interior Cache**: `_price_cache` stores API results for 1 hour to avoid rate limits.
*   **Refresh Button**: Clears BOTH caches to force fresh data.

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
