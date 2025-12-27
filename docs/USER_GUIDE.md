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

### Configurazione

Crea file `.env` con:
```
DATABASE_URL=postgresql://user:pass@host/db

# Telegram (Opzionale)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

#### 🤖 Setup Telegram Bot
1. Apri Telegram e cerca **@BotFather**.
2. Invia `/newbot` e segui le istruzioni per creare un bot.
3. Copia il **Token API** fornito.
4. Cerca **@userinfobot** (o simili) e invia un messaggio per ottenere il tuo **ID numerico** (Chat ID).
5. Inserisci entrambi nel file `.env`.
6. **Importante:** Invia un primo messaggio "Ciao" al tuo nuovo bot per inizializzare la chat.

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
- **Export CSV**: Pulsante nella toolbar per esportare tutte le holdings in formato CSV.

---

## 📰 Intelligence & RSS Feeds

### Fonti Supportate

Il sistema supporta due tipi di fonti per l'intelligence:

| Tipo | Esempio | Dati Estratti |
|------|---------|---------------|
| **YouTube** | @PaoloColetti | Trascrizioni → Riassunti AI |
| **RSS Feed** | Yahoo Finance | Titoli + Link articoli |

### RSS Feeds Preconfigurati

- Yahoo Finance (Market News)
- Bloomberg Markets
- CNBC Business
- Reuters Business

### Gestione Fonti

1. Vai in **Intelligence** dalla sidebar
2. Espandi **Manage Sources**
3. Incolla URL YouTube o RSS Feed
4. Clicca **+** per aggiungere

---

## ⏰ Scansioni Automatiche (Scheduler)

### Jobs Configurati

Il sistema esegue automaticamente queste scansioni:

| Job | Orario | Descrizione |
|-----|--------|-------------|
| `morning_scan` | 08:00 CET | Intelligence scan completo |
| `evening_scan` | 18:00 CET | Intelligence scan completo |
| `alert_check` | Ogni 5 min (08-22) | Controllo price alerts |

### API Endpoint

- **Lista Jobs**: `GET /api/scheduler/jobs`
- **Trigger Manuale**: `POST /api/scheduler/run-now`

---

## 🔔 Sistema di Alert

### Cos'è

Il sistema di Alert ti permette di impostare notifiche automatiche quando un ticker raggiunge un prezzo target.

### Come Usarlo

1. **Vai in Alerts** dalla sidebar (icona campanello)
2. **Clicca "New Alert"**
3. **Compila il form**:
   - **Ticker**: Simbolo (es. AAPL, TSLA, BTC-USD)
   - **Target Price**: Prezzo obiettivo
   - **Direction**: `Above` (≥) o `Below` (≤)
4. **Clicca "Create Alert"**

### Notifiche

Quando un alert viene triggerato:
- ✅ Viene segnato come `triggered` nel database
- ✅ Notifica Telegram inviata (se configurato)
- ✅ Alert rimosso dalla lista attivi

### API Endpoints

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/alerts` | Lista alerts attivi |
| POST | `/api/alerts` | Crea nuovo alert |
| DELETE | `/api/alerts/{id}` | Elimina alert |
| POST | `/api/alerts/check` | Controllo manuale |

---

## 📈 Analytics & Performance

La nuova sezione **Analytics** (Fase 3) offre strumenti avanzati per monitorare l'andamento del portfolio nel tempo e valutare il rischio.

### Dashboard Analytics
Accessibile tramite il pulsante 📊 nella sidebar (sotto Alerts).

**Funzionalità principali:**
1.  **Performance Chart**: Grafico interattivo che mostra l'andamento percentuale del portfolio.
    *   **Periodi**: 7D, 30D, 90D, 1Y.
    *   **Confronto Benchmark**: Puoi attivare/disattivare il confronto con S&P 500, NASDAQ 100 e MSCI World.
2.  **Risk Metrics**:
    *   **Sharpe Ratio**: Misura il rendimento corretto per il rischio.
    *   **Volatility**: Volatilità annualizzata del portfolio.
    *   **Max Drawdown**: La massima perdita registrata da un picco precedente.
3.  **Net Worth Tracker**: Valore totale del portfolio aggiornato all'ultimo snapshot.

### Portfolio Snapshots
Il sistema salva automaticamente uno "snapshot" del valore del portfolio ogni giorno alle **22:00 CET** (dopo la chiusura dei mercati USA).

*   **Salvataggio Manuale**: Puoi forzare un salvataggio in qualsiasi momento cliccando il pulsante "Save Snapshot" nella pagina Analytics.
*   **Nota**: I grafici e le metriche di rischio inizieranno a popolare i dati solo dopo aver accumulato almeno 2 snapshot giornalieri (minimo 2 giorni).

### API Endpoints
Endpoints per accedere ai dati analytics:

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `POST` | `/api/analytics/snapshot` | Crea manualmente uno snapshot giornaliero |
| `GET` | `/api/analytics/history` | Recupera la serie storica (`?days=30`) |
| `GET` | `/api/analytics/benchmarks` | Recupera i dati di confronto benchmark |
| `GET` | `/api/analytics/risk-metrics` | Calcola Sharpe, Volatilità, Drawdown |

---

## 🤖 Telegram Bot

### Cos'è

Il bot Telegram invia notifiche push quando i tuoi price alerts vengono attivati.

### Configurazione

1. **Crea il Bot**:
   - Apri Telegram → cerca `@BotFather`
   - Invia `/newbot` e segui le istruzioni
   - Copia il **Bot Token**

2. **Ottieni Chat ID**:
   - Cerca `@userinfobot` su Telegram
   - Invia qualsiasi messaggio
   - Copia il tuo **Chat ID**

3. **Configura .env**:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_CHAT_ID=987654321
   ```

### Formato Notifiche

```
🔔 PRICE ALERT TRIGGERED!

📈 AAPL
Target: ≥ $200.00
Current: $205.50

⏰ 2025-12-24 10:30:00
```

### Test Connessione

```bash
# Invia messaggio di test
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>&text=Test War Room"
```

---

## 📤 Export CSV Holdings

### Come Esportare

1. Vai nella **Dashboard** (Portfolio)
2. Clicca il pulsante **📥 Export CSV** nella toolbar superiore
3. Il file CSV viene scaricato automaticamente

### Formato CSV

```csv
ticker,name,broker,type,quantity,current_price,current_value,pct_change_1d,pnl_net,weight
AAPL,Apple Inc,IBKR,STOCK,10,195.50,1955.00,1.25,+350.00,5.5%
...
```

### API Endpoint

```bash
GET /api/portfolio/export-csv
```

Restituisce direttamente il file CSV con `Content-Disposition: attachment`.

---

## 🔄 Universal Ingestion (Reset DB)

### Funzionalità
Il sistema permette di **ricaricare completamente il database** partendo dai file sorgente processati. Questa operazione:
1.  **CANCELLA** tutte le transazioni e le holdings attuali.
2.  **RICARICA** i dati dai file JSON verificati in `scripts/`.
3.  **RICALCOLA** il portafoglio da zero.

### Quando Usarlo
- Dopo aver aggiunto nuovi documenti mensili (processati prima dagli script di ingestion).
- Se si notano disallineamenti o dati corrotti.
- Per allineare il DB dopo aver modificato le logiche di calcolo.

### Come Eseguire
1.  Vai nella **Dashboard**.
2.  Clicca il pulsante rosso **RESET DB** (in alto a destra).
3.  Conferma l'avviso di sicurezza.
4.  Attendi il messaggio "Ingestion Completa!".

**⚠️ ATTENZIONE:** Tutte le modifiche manuali (es. depositi fittizi aggiunti via UI) verranno PERSE se non sono state salvate nei file JSON sorgente.

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

### Telegram Bot Non Funziona

```
Telegram notification failed: Unauthorized
```

**Soluzione**: Verifica che `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` siano corretti nel file `.env`.

### Scheduler Non Parte

```
Scheduler failed to start
```

**Soluzione**: Verifica che APScheduler sia installato (`pip install apscheduler`).

### Valori Gonfiati (10x o 100x)

Se un titolo (es. su borsa di Londra/LSE) mostra un valore assurdo:

**Causa**: Il titolo è quotato in **Pence (GBp)** ma il sistema lo leggeva come **Sterline (GBP)**.
**Soluzione**: Il fix automatico è stato applicato. Se persiste, cancella la cache:
```bash
del data/forex_cache.json
```
e riavvia il backend.

### Dashboard Mostra Dati Vecchi

Se i totali non tornano (es. 18k invece di 4k) dopo una correzione:

**Soluzione**: Esegui un refresh forzato dello snapshot API o attendi le 22:00.
```bash
curl -X POST http://localhost:8000/api/refresh
```

---

## 📞 Supporto

Per problemi tecnici, controllare i log dello script o contattare il supporto.

---

*Ultimo aggiornamento: Dicembre 2025*
