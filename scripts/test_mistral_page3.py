"""
MISTRAL TRANSACTION EXTRACTOR (Page 3 Test)
===========================================
Extracts complex multi-line transactions using Mistral.
Focus: Page 3 of BG Saxo PDF (Qualcomm Dividend blocks)
"""
import json
import requests
import fitz

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

def extract_page_3_transactions():
    pdf_path = r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf"
    
    # 1. Get Page 3 Text
    doc = fitz.open(pdf_path)
    page_text = doc[2].get_text("text") # 0-indexed, so 2=Page 3
    doc.close()
    
    print("PAGE 3 CONTENT:")
    print("-" * 50)
    print(page_text[:1000] + "...")
    print("-" * 50)
    print()
    
    # 2. Ask Mistral
    PROMPT = f"""Azzera la tua memoria precedente. Sei un estrattore di dati preciso.

Ecco il testo grezzo di una pagina di estratto conto:
{page_text}

IDENTIFICA LE TRANSAZIONI.
Ogni transazione è un blocco di testo. Cerca:
- Data (se presente) o periodo
- Tipo (Acquisto, Vendita, Dividendo)
- Nome Asset (es: Qualcomm Inc.)
- Quantità
- Importo
- ISIN

Estrai in JSON:
{{
  "transactions": [
    {{
      "type": "DIVIDEND/BUY/SELL",
      "asset": "Qualcomm Inc.",
      "isin": "US...",
      "amount": 0.96,
      "currency": "EUR",
      "details": "Dividendo per azione..."
    }}
  ]
}}"""

    print("Calling Mistral...")
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json().get("response", "")
        print("\nMISTRAL EXTRACTION:")
        print(result)
        
        # Parse validation
        try:
            data = json.loads(result)
            print(f"\nExtracted {len(data.get('transactions', []))} transactions successfully.")
        except:
            print("JSON Parsing failed")
            
if __name__ == "__main__":
    extract_page_3_transactions()
