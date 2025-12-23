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

### 3. Start Services (One-Click) 🟢
Simply double-click the `Start_WarRoom.bat` file in the root directory.
It automatically:
- Checks for free ports
- Starts Docker containers (Postgres & Chroma)
- Launches Ollama (WSL)
- Activates Python Environment & Starts Backend
- Launches Svelte Frontend

### 4. Shutdown (One-Click) 🔴
Double-click `Shutdown_WarRoom.bat` to safely stop all services and free up ports.

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
    - **6-Tile Grid**: Assets automatically categorized (Stocks, ETFs, Bonds, Crypto, Commodities, Cash).
    - **Interactive Filtering**: Real-time broker filter bar (IBKR, BG SAXO, etc.) that updates all asset tiles.
    - **Advanced Metrics**: Daily P&L (€ and %) integrated into KPI tiles and broker breakdown.
    - **Data-Dense Layout**: Full-width compact tables with interactive sorting (asc/desc) on all columns.
    - **Modern UI**: Dark Mode with glassmorphism, responsive single-column stack layout.
- ✅ Sentiment analysis from news & social media
- ✅ Macro scenario generation
- ✅ Mobile access via Cloudflare Tunnel
- ✅ Telegram bot for quick trades & alerts

## 🔒 Security

- All sensitive data stored locally
- AI runs on local hardware (Ollama)
- No cloud dependencies for core functionality
- JWT authentication for API access

## 📜 License

MIT - Personal use only
