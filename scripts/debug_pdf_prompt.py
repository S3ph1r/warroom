
import requests
import json
import sys

# The text exactly as extracted from the log
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
-132,66 EUR"""

# The prompt we are testing
PROMPT = f"""Analizza questo documento finanziario PDF:
    
{SAMPLE_TEXT}

ISTRUZIONI CATEGORIA:
- TRANSACTIONS: Contiene operazioni di trading individuali (Buy/Sell, Acquista/Vendi, Kauf/Verkauf) con date, quantità e prezzi.
- HOLDINGS: Snapshot posizioni attuali del portafoglio (Posizioni, Portfolio, Saldo titoli).
- CASH_MOVEMENTS: Solo movimenti di cassa (depositi, prelievi, fees).
- TAX_REPORT: Documenti fiscali, certificati, report annuali.
- ACCOUNT_STATEMENT: Estratti conto periodici senza dettaglio operazioni.
- OTHER: Altro (privacy policy, annunci).

Rispondi SOLO JSON:
{{
  "should_process": true se contiene dati utili per portafoglio (es. "Eseguito", "Executed", "Acquisto", "Vendita", "Buy", "Sell"),
  "document_type": "STOCKS" | "CRYPTO" | "COMMODITIES" | "CASH_MOVEMENTS" | "UNKNOWN",
  "document_category": "TRANSACTIONS" | "HOLDINGS" | "CASH_MOVEMENTS" | "TAX_REPORT" | "ACCOUNT_STATEMENT" | "OTHER",
  "processing_strategy": "EXTRACT_TRANSACTIONS" | "EXTRACT_HOLDINGS" | "EXTRACT_CASH" | "SKIP",
  "asset_type": "STOCK" | "ETF" | "CRYPTO" | "COMMODITY" | "CASH",
  "content_summary": "breve descrizione"
}}
"""

def call_ollama(prompt):
    print(f"Sending prompt ({len(prompt)} chars)...")
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
