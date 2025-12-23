# WAR ROOM - Guida Utente

> Sistema di monitoraggio portafoglio multi-broker

## 📋 Indice

1. [Setup Iniziale](#setup-iniziale)
2. [Documenti per Broker](#documenti-per-broker)
3. [Ingestion Iniziale](#ingestion-iniziale)
4. [Aggiornamento Mensile](#aggiornamento-mensile)
5. [Dashboard](#dashboard)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Setup Iniziale

### Requisiti

- Python 3.10+
- PostgreSQL database (Neon)
- Virtual environment

### Installazione

```bash
cd warroom
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Configurazione

Crea file `.env` con:
```
DATABASE_URL=postgresql://user:pass@host/db
```

---

## 📁 Documenti per Broker

### BG SAXO

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Posizioni** | `Posizioni_DD-mmm-YYYY_HH_MM_SS.csv` | CSV | ✅ Sì |
| Transazioni | `Transactions_*.pdf` | PDF | ⭐ Opzionale |

**Come esportare:**
1. Accedi a BG Saxo → Portfolio → Posizioni
2. Clicca "Esporta" → CSV
3. Salva in `D:\Download\BGSAXO\`

---

### TRADE REPUBLIC

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Estratto Conto** | `Documento_*.pdf` | PDF | ✅ Sì |

**Come esportare:**
1. App Trade Republic → Profilo → Documenti
2. Scarica tutti gli estratti conto
3. Salva in `D:\Download\Trade Repubblic\`

---

### IBKR (Interactive Brokers)

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Transaction History** | `U*.TRANSACTIONS.1Y.csv` | CSV | ✅ Sì |

**Come esportare:**
1. Client Portal → Performance & Reports → Transaction History
2. Export → CSV (ultimo anno)
3. Salva in `D:\Download\IBKR\`

---

### SCALABLE CAPITAL

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Financial Status** | `YYYYMMDD Financial Status*.pdf` | PDF | ✅ Sì |
| Monthly Statements | `YYYYMMDD Monthly account statement*.pdf` | PDF | ⭐ Opzionale |

**Come esportare:**
1. Scalable Capital → Documenti → Rendiconti
2. Scarica "Financial Status" più recente
3. Salva in `D:\Download\SCALABLE CAPITAL\`

---

### REVOLUT

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Trading Statement** | `trading-account-statement_*.pdf` | PDF | ✅ Sì |
| **Crypto Statement** | `crypto-account-statement_*.pdf` | PDF | ✅ Sì |

**Come esportare:**
1. Revolut App → Stocks → Statement → Generate
2. Revolut App → Crypto → Statement → Generate
3. Salva in `D:\Download\Revolut\`

---

### BINANCE

| Documento | Nome File | Tipo | Obbligatorio |
|-----------|-----------|:----:|:------------:|
| **Transaction Export** | `YYYY_MM_DD_HH_MM_SS.csv` | CSV | ✅ Sì |

**Come esportare:**
1. Binance → Wallet → Transaction History → Export
2. Seleziona periodo completo
3. Salva in `D:\Download\Binance\`

---

## 🔄 Ingestion Iniziale

### Prerequisiti

1. Scarica **tutti i documenti obbligatori** per ogni broker
2. Posizionali nelle cartelle corrette

### Esecuzione

```bash
cd warroom
.\venv\Scripts\activate

# Esegui ingestion completa
python scripts/initial_ingestion.py
```

### Risultato Atteso

```
✅ ALL INGESTION STEPS COMPLETED SUCCESSFULLY!
  Holdings: ~111
  Transactions: ~1,739
  Total Value: ~€35,639
```

### In caso di errore

```bash
# Riprendi dal punto di fallimento
python scripts/initial_ingestion.py --resume

# Esegui solo uno step specifico
python scripts/initial_ingestion.py --step 5
```

---

## 📅 Aggiornamento Mensile

### Documenti da Scaricare

| Broker | Documento | Frequenza |
|--------|-----------|:---------:|
| BG Saxo | `Posizioni_*.csv` | Mensile |
| Trade Republic | Nuovi estratti | Mensile |
| IBKR | `U*.TRANSACTIONS.1Y.csv` | Mensile |
| Scalable | `Financial Status*.pdf` | Mensile |
| Revolut | Entrambi gli statements | Mensile |
| Binance | Transaction export | Mensile |

### Procedura

1. Scarica i nuovi documenti
2. Sostituisci i vecchi file (o aggiungi i nuovi)
3. Esegui ingestion:

```bash
python scripts/initial_ingestion.py
```

---

## 📊 Dashboard

### Avvio
```bash
# Backend (Port 8000)
cd backend
uvicorn main:app --reload --port 8000

# Frontend (Port 5200)
cd ../frontend
npm run dev
```

### URL

Apri [http://localhost:5200](http://localhost:5200) (Frontend)
Interfaccia API: [http://localhost:8000/docs](http://localhost:8000/docs)

### Funzionalità

- **KPI Totali**: Net Worth, P&L Netto e P&L Giornaliero (1D).
- **Broker Allocation**: Tile interattive per broker con valore, % peso, e performance (1D/Net).
- **Filtro Broker**: Barra superiore per isolare i dati di un singolo broker in tempo reale.
- **Asset Table (6 Tile)**: Tabella dedicata per Stocks, ETFs, Bonds, Crypto, Commodities, Cash.
- **Ordinamento**: Clicca sulle intestazioni per ordinare ogni tabella per qualsiasi valore.
- **Charts**: Allocazione visuale per Asset e per Broker.

---

## 🔧 Troubleshooting

### Errore Encoding (Windows)

```
UnicodeEncodeError: 'charmap' codec can't encode
```

**Soluzione**: Lo script usa già UTF-8 encoding. Se persiste, eseguire:
```bash
set PYTHONIOENCODING=utf-8
python scripts/initial_ingestion.py
```

### Database Connection Error

```
could not connect to server
```

**Soluzione**: Verifica `.env` e connessione internet.

### Parser Non Trova File

```
FileNotFoundError: No CSV files found
```

**Soluzione**: Verifica che i file siano nella cartella corretta con i nomi attesi.

---

## 📞 Supporto

Per problemi tecnici, controllare i log dello script o contattare il supporto.

---

*Ultimo aggiornamento: Dicembre 2025*
