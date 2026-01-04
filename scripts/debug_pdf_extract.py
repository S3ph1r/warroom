
import requests
import json
import sys
import re

# The text exactly as extracted from the log (messy PDF text)
SAMPLE_TEXT = """BG SAXO SIM - B2C 1 Cash / Corso Europa 22 / 20122 Milan / Italy
/ Email: supporto@bgsaxo.it
Pagina 2 di 83
Roberto Guareschi
Valuta:EUR
Conto/i: 65500/100461E00
Periodo di rendicontazione
26-nov-2024 - 19-dic-2025
Generata il: 19-dic-2025
Tipo Nome prodotto Tipo Importo contabilizzato Contanti
19-dic-2025
Contrattazione Alphabet Inc. Class A Acquista 2 @ 301,93 Pending -
ID contrattazione
5353555477
ID contrattazione
5353555477
18-dic-2025 -1.170,68 1.362,01
Contrattazione ServiceNow Inc. Acquista 1 @ 155,29 USD -133,51 -
Commissione
-0,85 EUR
Valorenegoziato
-132,66 EUR
Costo di conversione valuta
-0,33
Costo totale
-1,18 EUR"""

# The NEW Generalized Prompt from smart_extractor.py
PROMPT = f"""
Task: Extract financial transactions from the following text into JSON.
Document Type: STOCKS

Text Content:
\"\"\"
{SAMPLE_TEXT}
\"\"\"

Return a JSON object with a key "rows".

INSTRUCTIONS:
1. Identify any list or table of financial movements.
2. Look for lines containing a DATE (YYYY-MM-DD or DD-MM-YYYY) and an AMOUNT (money value).
3. Ignore headers, footers, and page numbers.
4. Extract the following fields for each transaction line:

Fields:
- "date": Transaction date (YYYY-MM-DD format).
- "symbol": Ticker, ISIN, or Asset Name (if present).
- "description": Description of the operation (e.g. "Buy Apple", "Dividend Payment").
- "quantity": Number of units (if applicable).
- "price": Price per unit (if applicable).
- "amount": Total value of the transaction.
- "currency": Currency code (EUR, USD, etc.).
- "operation": Infer from context: PURCHASE, SALE, DIVIDEND, DEBIT, CREDIT, FEE.

CRITICAL RULES:
- If "amount" is negative, it is usually a COST/PURCHASE or FEE.
- If "amount" is positive, it is usually a SALE or DIVIDEND.
- Capture ALL transactions found in the text.

Example JSON:
{{ "rows": [ {{ "date": "2023-01-01", "symbol": "AAPL", "quantity": 10, "amount": -1500.00, "currency": "USD", "operation": "PURCHASE" }} ] }}

Strictly output valid JSON only.
"""

def call_ollama(prompt):
    print(f"Sending extraction prompt ({len(prompt)} chars)...")
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:14b-instruct-q6_K",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json().get('response', '')
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    response = call_ollama(PROMPT)
    print("\n--- RESPONSE FROM LLM ---")
    print(response)
    print("\n--- END RESPONSE ---")
