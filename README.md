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

### 3. Start Services
```bash
# Start PostgreSQL + Ollama + ChromaDB
docker-compose up -d

# Initialize database
python scripts/init_db.py

# Run dashboard
streamlit run dashboard/app.py
```

## 📁 Project Structure

```
warroom/
├── api/              # FastAPI REST endpoints
├── dashboard/        # Streamlit UI
├── ingestion/        # CSV parsers for brokers
├── intelligence/     # News & sentiment scrapers
├── ai/               # Ollama & RAG integration
├── db/               # Database models & migrations
├── config/           # Settings & configuration
├── scripts/          # Utility scripts
└── tests/            # Unit tests
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
