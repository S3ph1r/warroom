# 📋 Guida Utente - War Room

## 🚀 Setup Iniziale

Questa guida ti aiuta a configurare War Room per la prima volta e a mantenerlo aggiornato.

---

## 📁 PASSO 1: Prepara le Cartelle

Crea la seguente struttura su Google Drive (o locale):

```
📁 WAR_ROOM_DATA/
├── 📁 inbox/
│   ├── 📁 bgsaxo/
│   ├── 📁 scalable/
│   ├── 📁 binance/
│   ├── 📁 revolut/
│   ├── 📁 traderepublic/
│   └── 📁 ibkr/
└── 📁 processed/
```

---

## 📥 PASSO 2: Scarica i Documenti dai Broker

### BG Saxo ⭐
1. Accedi a **SaxoTraderGO** o **SaxoInvestor**
2. Vai su **Account** → **Reports** → **Positions**
3. Esporta come **CSV**
4. Salva in `inbox/bgsaxo/`

**File richiesto**: `Posizioni_*.csv`

---

### Scalable Capital ⭐
1. Accedi all'app o web
2. Vai su **Profilo** → **Documenti**
3. Scarica **"Financial Status"** (Stato Finanziario)
4. Salva in `inbox/scalable/`

**File richiesto**: `Financial status*.pdf`

---

### Binance ⭐
1. Accedi a Binance
2. Vai su **Wallet** → **Account Statement**
3. Genera un **Account Statement** per il periodo desiderato
4. Scarica il PDF (richiede password, solitamente quella del tuo account)
5. Salva in `inbox/binance/`

**File richiesto**: `AccountStatementPeriod_*.pdf`

---

### Revolut

#### Stocks ⭐
1. Apri l'app Revolut → **Invest**
2. Tocca **More (...)** → **Documents** → **Stocks**
3. Seleziona **Account Statement**
4. Scarica il PDF
5. Salva in `inbox/revolut/`

**File richiesto**: `trading-account-statement_*.pdf`

#### Crypto e Commodities (Oro/Argento) ⚠️
Revolut **NON** fornisce snapshot delle posizioni per crypto e commodities.

**Soluzione**: Fai uno **screenshot** dalla app:
1. Apri la sezione **Crypto** e fai screenshot
2. Apri la sezione **Commodities** (Oro/Argento) e fai screenshot
3. Salva gli screenshot in `inbox/revolut/`

---

### Trade Republic ⚠️
Trade Republic **NON** fornisce uno snapshot delle posizioni.

**Soluzione**:
1. Apri l'app Trade Republic
2. Vai alla home page dove vedi tutti i tuoi titoli
3. Fai uno **screenshot**
4. Salva in `inbox/traderepublic/`

**Opzionale**: Scarica anche `Estratto conto.pdf` per lo storico transazioni.

---

### Interactive Brokers (IBKR) ⚠️
Il report di default non include le posizioni aperte.

**Configurazione una tantum**:
1. Accedi a **Client Portal**
2. Vai su **Performance & Reports** → **Statements**
3. Clicca su **Custom Statements** → **Create**
4. Seleziona:
   - ✅ Open Positions
   - ✅ Trades
   - ✅ Cash Report
5. Salva il template
6. Esporta in **CSV**
7. Salva in `inbox/ibkr/`

---

## 🔄 PASSO 3: Importa i Dati

Una volta scaricati tutti i documenti, esegui l'importazione:

```bash
cd warroom
python scripts/import_all_data.py
```

---

## 📆 Aggiornamenti Mensili

Ogni mese (o trimestre), ripeti questi passaggi:

### Checklist Mensile

#### Download Automatici
- [ ] **BG Saxo**: Scarica `Posizioni_*.csv`
- [ ] **Scalable**: Scarica `Financial status.pdf`
- [ ] **Binance**: Scarica `AccountStatementPeriod_*.pdf`
- [ ] **Revolut Stocks**: Scarica `trading-account-statement_*.pdf`

#### Screenshot Richiesti
- [ ] **Revolut Crypto**: Screenshot sezione Crypto
- [ ] **Revolut Commodities**: Screenshot sezione Oro/Argento
- [ ] **Trade Republic**: Screenshot home page titoli

#### Opzionali
- [ ] **IBKR**: Esporta Activity Statement con Open Positions

---

## ❓ FAQ

### Perché alcuni broker richiedono screenshot?
Alcuni "neobroker" (Revolut, Trade Republic) non forniscono documenti con le posizioni attuali. Gli screenshot sono l'unico modo per catturare questi dati.

### Quanto spesso devo aggiornare?
- **Consigliato**: Mensile
- **Minimo**: Trimestrale

### I miei dati sono al sicuro?
Tutti i dati restano sul tuo computer. War Room non invia nulla a server esterni.

---

## 🆘 Supporto

Se hai problemi con l'importazione di un broker specifico, apri una issue su GitHub.
