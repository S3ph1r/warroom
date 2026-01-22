# 🎯 THE WAR ROOM

**Personal Investment Management System (PIMS)**

Sistema di gestione portafoglio investimenti con AI locale per analisi di scenario.

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone repository
git clone https://github.com/S3ph1r/warroom.git
cd warroom

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy template and edit with your values
copy .env.example .env
# Edit .env with your API keys and passwords
```

### 3. Deployment Options

#### Option A: Standalone (Recommended for development)
Simply double-click the `Start_WarRoom.bat` file in the root directory.
It automatically:
- Starts Docker containers (Postgres & Chroma)
- Launches Ollama (WSL)
- Launches Svelte Frontend

#### Option B: Integrated (Neural-Home Infrastructure)
Deploy to LXC 106 and connect to shared NHI services:
- **Database**: Use LXC 105 (Postgres)
- **AI Brain**: Connect to [NHI Orchestrator](https://github.com/S3ph1r/Neural-home-infrastructure) via `OLLAMA_API_BASE`.
- **UI**: Served via Nginx on LXC 106.

See [Infrastructure v2](docs/INFRASTRUCTURE_V2.md) for detailed homelab topology.

### 4. Shutdown 🔴
Double-click `Shutdown_WarRoom.bat` (Standalone) or `systemctl stop warroom-backend` (Linux).

---

### Alternative: Manual Start
```bash
# Start PostgreSQL + Ollama + ChromaDB
docker-compose up -d

# Initialize database
python scripts/init_db.py

# Start Backend (FastAPI)
cd backend
uvicorn main:app --reload --port 8000

# Start Frontend (Svelte)
cd ../frontend
npm install
npm run dev
```

## 📁 Project Structure

```
warroom/
├── backend/           # FastAPI REST endpoints
├── frontend/          # Svelte/Vite UI
├── dashboard/         # Legacy Streamlit UI
├── ingestion/         # CSV parsers for brokers
├── intelligence/      # News & sentiment scrapers
├── ai/                # Ollama & RAG integration
├── db/                # Database models & migrations
├── config/            # Settings & configuration
├── scripts/           # Utility scripts
├── services/          # Real-time price services
└── tests/             # Unit tests
```

## 🏦 Supported Brokers

- Fineco
- Revolut
- BG Saxo
- Scalable Capital
- Trade Republic
- Interactive Brokers (IBKR)
- Binance
- Coinbase
- Crypto.com

## 📊 Features

- ✅ Multi-broker CSV import with automatic reconciliation
- ✅ Real-time portfolio tracking
- ✅ AI-powered market intelligence (local LLM)
- ✅ **The Council 3.0 (Matrix Architecture)**:
    - **Matrix Analysis**: 4 AI Models (Gemini, Claude, DeepSeek, Qwen) x 2 Roles (Historian, Strategist) = **8 Strategic Opinions**.
    - **President's Consensus**: A local LLM (Mistral) synthesizes all 8 opinions into a unified Executive Summary and scores the models' depth/sentiment.
    - **Granular Control**: "Sync" individual advisors to refresh specific opinions without re-running the full council.
    - **Smart Caching**: Daily session persistence to minimize API costs and latency.
- ✅ **YouTube Intelligence 2.0**: 
    - Auto-scrape & summarize videos from finance channels (transcripts analysis)
    - **New Source**: "Altri Orienti" (Simone Pieranni) fully integrated.
    - **Smart Fallback**: Uses video description if transcripts are missing (no more skipped content).
    - **Localization**: Titles and Summaries automatically translated to **Italian**.
- ✅ **v5 Dashboard (Svelte/FastAPI)**: 
    - **Turbo Mode (Stale-While-Revalidate)**: Instant zero-latency load using cached snapshots, with background refresh and auto-polling updates.
    - **6-Tile Grid**: Assets automatically categorized (Stocks, ETFs, Bonds, Crypto, Commodities, Cash).
    - **Interactive Filtering**: Real-time broker filter bar (IBKR, BG SAXO, etc.) that updates all asset tiles.
    - **Advanced Metrics**: Daily P&L (€ and %) integrated into KPI tiles and broker breakdown.
    - **Data-Dense Layout**: Full-width compact tables with interactive sorting (asc/desc) on all columns.
    - **Modern UI**: Dark Mode with glassmorphism, responsive single-column stack layout.
    - **Export CSV**: One-click portfolio export with all holdings data.
- ✅ Sentiment analysis from news & social media
- ✅ Macro scenario generation
- ✅ Mobile access via Cloudflare Tunnel
- ✅ **Price Alert System**:
    - Set target price alerts (above/below thresholds)
    - Automated 5-minute checks during market hours (08:00-22:00 CET)
    - UI manager for creating, viewing, and deleting alerts
- ✅ **Telegram Bot Integration**:
    - Push notifications when price alerts trigger
    - Real-time alerts to your phone
    - Easy setup via @BotFather
- ✅ **Scheduled Intelligence Scans**:
    - Morning scan (08:00 CET) & Evening scan (18:00 CET)
    - APScheduler integration with FastAPI
    - API endpoints for manual triggers
- ✅ **Analytics & Metrics v1**:
    - Daily Portfolio Snapshots (22:00 CET)
    - Performance Chart vs Benchmarks (S&P500, NASDAQ, MSCI)
    - Risk Analysis (Sharpe Ratio, Volatility, Drawdown)
- ✅ **Multi-Currency Engine v2**:
    - Robust `GBp` (Pence) handling for LSE stocks
    - Auto-conversion for USD, HKD, DKK, CHF -> EUR
- ✅ **Universal Ingestion System 3.0 (Smart & Agnostic) 🤖**: 
    - **Fully Automated Pipeline**: Orchestrator → Classifier → Extractor → Loader.
    - **Smarter Classification**: Text-First strategy for native PDFs (80 files in 8 mins) with Vision fallback for scans.
    - **Hybrid Extraction**: High-precision extraction of `quantity`, `price`, and `total_amount` using local LLMs (Qwen/Mistral).
    - **Universal Normalization**: Broker-agnostic `OPERATION_MAP` handles BUY, SELL, DIVIDEND, FEE, TRANSFER_IN across all platforms.
    - **BG Saxo Refinement**: Automatic Ticker/Market splitting (`INTC:xnas` → `INTC` | `xnas`) for cleaner data.
    - **Scalable Capital Refinement**: Intelligent Asset Type detection (Stock vs ETF) and ISIN-based pricing.
    - **Validated Brokers**: Full end-to-end support for **Revolut**, **Scalable Capital**, **BG Saxo**, and **IBKR**.
    - **Unified Traceability**: Centralized logging in `warroom_ingestion.log` for debugging the entire pipeline.
    - **Atomic DB Loading**: History-based holdings calculation with WAC (Weighted Average Cost) and Cash balance tracking.
    - **Advanced Binance Integration**: 
        - **Historic Pricing**: Parallel fetching of historical prices (50 threads) for accurate WAC calculation.
        - **Full Asset Support**: Seamlessly handles Spot, Earn, Staking, Airdrops, and Rewards.
        - **Smart Reconciliation**: Merges Spot and Earn balances for a unified view of asset ownership.
    - **Robust Persistence**: Atomic file writing to prevent data corruption during high-concurrency updates.

## 🔒 Security

- All sensitive data stored locally
- AI runs on local hardware (Ollama)
- No cloud dependencies for core functionality
- JWT authentication for API access

## 📜 License

MIT - Personal use only
