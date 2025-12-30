"""
IDP Pipeline - Prompts for Code Generation
Contains prompt templates for LLM to generate parser code.
NOTE: All curly braces in code snippets must be doubled {{ }} to escape .format()
"""

# =============================================================================
# ITALIAN DATE HANDLING HELPER (included in all prompts)
# Curly braces are escaped with {{ }} for .format() compatibility
# =============================================================================

ITALIAN_DATE_HELPER = """
NOTA CRITICA - DATE IN ITALIANO:
Le date italiane usano abbreviazioni dei mesi in italiano. Devi convertire usando questa mappa:
ITALIAN_MONTHS = {{
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06',
    'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}}

Esempio conversione "19-dic-2025" → "2025-12-19":
```python
import re
def parse_italian_date(date_str):
    italian_months = {{'gen':'01','feb':'02','mar':'03','apr':'04','mag':'05','giu':'06',
                      'lug':'07','ago':'08','set':'09','ott':'10','nov':'11','dic':'12'}}
    match = re.match(r'(\\d{{1,2}})-([a-zA-Z]{{3}})-(\\d{{4}})', date_str)
    if match:
        day, month, year = match.groups()
        month_num = italian_months.get(month.lower(), '01')
        return f"{{year}}-{{month_num}}-{{day.zfill(2)}}"
    return None
```
USA SEMPRE QUESTA FUNZIONE per convertire le date!
"""

# =============================================================================
# CSV PARSER GENERATION
# =============================================================================

PROMPT_CSV_HOLDINGS = """Sei un Senior Data Engineer Python. Devi scrivere una funzione per parsare un CSV di holdings/posizioni finanziarie ITALIANO.

REQUISITI:
1. La funzione deve chiamarsi `parse(file_path: str) -> list[dict]`
2. Usa `pd.read_csv(..., sep=None, engine='python')` per auto-rilevare il separatore
3. NOMI COLONNE ITALIANI: Il file ha colonne come "Strumento", "Quantità", ecc.
4. HEADER DINAMICO: L'intestazione potrebbe non essere alla riga 0. Cerca la riga che contiene "Strumento" o "Ticker".
5. FILTRA: Ignora righe vuote o di riepilogo.

MAPPING COLONNE ITALIANE (nomi comuni):
- "Strumento" / "Descrizione" / "Nome" → name
- "Simbolo" / "Ticker" / "Codice" → ticker  
- "ISIN" → isin
- "Quantità" / "Qty" → quantity
- "Valuta" / "Currency" → currency
- "Prz. corrente" / "Prezzo corrente" / "Ultimo prezzo" → current_price
- "Prezzo di apertura" / "Prezzo acquisto" → purchase_price
- "Valore" / "Controvalore" / "Esposizione" → current_value
- "Tipo" / "Asset class" → asset_type

SAMPLE DATA (prime righe):
{sample_content}

TARGET SCHEMA - Restituisci una lista di dict:
- ticker: str (estrai da colonna Ticker/Simbolo, o da parti del Nome, o ISIN)
- name: str
- isin: str
- quantity: float 
- currency: str (default 'EUR')
- current_price: float (opzionale)
- current_value: float
- asset_type: str (STOCK, ETF, BOND, FUND)

LOGICA ESTRAZIONE TICKER:
- Se c'è colonna "Simbolo" o "Ticker", usala
- Altrimenti estrai le prime lettere maiuscole dal nome (es. "Apple Inc." → "AAPL")
- Come fallback, usa l'ISIN

IMPORTANTE - NUMERI EUROPEI:
```python
def clean_number(val):
    if pd.isna(val) or str(val).strip() == '': return 0.0
    s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip()
    try: return float(s)
    except: return 0.0
```

Restituisci SOLO il codice Python:
```python
import pandas as pd
import re

def parse(file_path: str) -> list[dict]:
    # Read CSV
    df = pd.read_csv(file_path, encoding='utf-8')
    
    # Clean column names
    df.columns = [c.strip().strip('"') for c in df.columns]
    
    # Your parsing logic here...
    
    return results
```"""


PROMPT_CSV_TRANSACTIONS = """Sei un Senior Data Engineer Python. Devi scrivere una funzione per parsare un CSV di transazioni finanziarie.

REQUISITI:
1. La funzione deve chiamarsi `parse(file_path: str) -> list[dict]`
2. Usa pandas per leggere il CSV
3. Gestisci encoding UTF-8 e separatori , o ;
4. FILTRA le righe non valide (intestazioni ripetute, subtotali)
""" + ITALIAN_DATE_HELPER + """

SAMPLE DATA (prime 50 righe):
{sample_content}

TARGET SCHEMA - La funzione deve restituire una lista di dict con questi campi:
- date: str (formato YYYY-MM-DD)
- ticker: str (simbolo strumento)
- isin: str (opzionale)
- operation: str (BUY, SELL, DIVIDEND, FEE, DEPOSIT, WITHDRAW)
- quantity: float
- price: float (prezzo unitario)
- total_amount: float (importo totale)
- currency: str
- fees: float (commissioni, default 0)

MAPPING OPERAZIONI:
- Acquista, Buy, Acquisto → BUY
- Vendi, Sell, Vendita → SELL
- Dividendo, Dividend → DIVIDEND
- Commissione, Fee → FEE

NOTA NUMERI EUROPEI:
```python
def clean_number(val):
    if pd.isna(val) or val == '': return 0.0
    s = str(val).replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except: return 0.0
```

Restituisci SOLO il blocco di codice Python:
```python
import pandas as pd
import re

def parse(file_path: str) -> list[dict]:
    ...
```"""


# =============================================================================
# PDF PARSER GENERATION
# =============================================================================

PROMPT_PDF_HOLDINGS = """Sei un Senior Data Engineer Python. Devi scrivere una funzione per estrarre posizioni da un PDF finanziario.

REQUISITI:
1. La funzione deve chiamarsi `parse(file_path: str) -> list[dict]`
2. Usa pdfplumber per estrarre il testo
3. Analizza la struttura del documento per trovare le tabelle di holdings
4. Gestisci layout multi-colonna se presente

SAMPLE TEXT (prime 2-3 pagine):
{sample_content}

TARGET SCHEMA:
- ticker: str
- name: str  
- isin: str (opzionale, pattern: 2 lettere + 10 alfanumerici)
- quantity: float
- currency: str
- current_price: float (opzionale)
- current_value: float
- asset_type: str (STOCK, ETF, BOND, CRYPTO, COMMODITY)

NOTA NUMERI EUROPEI:
```python
def clean_number(text):
    if not text: return 0.0
    t = str(text).replace('.', '').replace(',', '.').strip()
    t = re.sub(r'[^\\d.-]', '', t)
    try: return float(t)
    except: return 0.0
```

STRATEGIA DI PARSING CONSIGLIATA:
1. Estrai tutto il testo pagina per pagina
2. Cerca pattern per ISIN: r'[A-Z]{{2}}[A-Z0-9]{{10}}'
3. Cerca numeri con formato europeo per quantità/valori
4. Raggruppa righe correlate (ISIN + Ticker + Quantità sulla stessa riga/blocco)

Restituisci SOLO il blocco di codice Python:
```python
import pdfplumber
import re

def parse(file_path: str) -> list[dict]:
    ...
```"""


PROMPT_PDF_TRANSACTIONS = """Sei un Senior Data Engineer Python. Devi scrivere una funzione per estrarre transazioni da un PDF finanziario.

REQUISITI:
1. La funzione deve chiamarsi `parse(file_path: str) -> list[dict]`
2. Usa pdfplumber per estrarre il testo
3. Mantieni lo "stato" della data corrente (spesso le date appaiono come intestazioni di gruppo)
4. Gestisci transazioni multi-riga (es. riga principale + riga commissioni)
""" + ITALIAN_DATE_HELPER + """

SAMPLE TEXT (pagine intermedie dove ci sono transazioni):
{sample_content}

TARGET SCHEMA:
- date: str (YYYY-MM-DD)
- ticker: str
- isin: str (opzionale)
- operation: str (BUY, SELL, DIVIDEND, FEE)
- quantity: float
- price: float
- total_amount: float
- currency: str
- fees: float (default 0)

NOTA NUMERI EUROPEI:
```python
def clean_number(text):
    if not text: return 0.0
    t = str(text).replace('.', '').replace(',', '.').strip()
    t = re.sub(r'[^\\d.-]', '', t)
    try: return float(t)
    except: return 0.0
```

STRATEGIA "STATEFUL PARSING":
1. Itera riga per riga
2. Quando trovi una DATA (pattern: \\d{{2}}-[a-zA-Z]{{3}}-\\d{{4}}), usa parse_italian_date() e salva come current_date
3. Quando trovi un'operazione (Acquista/Vendi), associa alla current_date
4. Se la riga successiva ha "Commissione", aggiungila alla transazione precedente

IMPORTANTE: Cerca pattern come:
- Date: "19-dic-2025", "05-gen-2024"
- Operazioni: "Acquista", "Vendi", "Dividendoincontanti"
- ISIN: 12 caratteri alfanumerici che iniziano con 2 lettere

Restituisci SOLO il blocco di codice Python:
```python
import pdfplumber
import re

def parse(file_path: str) -> list[dict]:
    ...
```"""


# =============================================================================
# SELF-CORRECTION PROMPT
# =============================================================================

PROMPT_FIX_ERROR = """Il parser che hai generato ha prodotto un errore.

CODICE ORIGINALE:
```python
{original_code}
```

ERRORE:
{error_message}

TRACEBACK:
{traceback}
""" + ITALIAN_DATE_HELPER + """

NOTA: Se l'errore riguarda il parsing di date come "19-dic-2025", usa OBBLIGATORIAMENTE la funzione parse_italian_date() mostrata sopra.

Correggi il codice per risolvere l'errore. Restituisci SOLO il codice Python corretto:
```python
...
```"""
