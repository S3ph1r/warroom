"""
Pattern Discovery Prompt

Ask Qwen to analyze the PDF text and tell us:
- What transaction types exist
- How many lines each one takes
- Where each field (date, name, qty, price, ISIN) is located

Then we build a deterministic parser from these rules.
"""
import requests
import pdfplumber
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# Extract first 10 pages 
print("📄 Extracting first 10 pages...")
with pdfplumber.open(pdf_path) as pdf:
    pages_text = []
    for i in range(min(10, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        pages_text.append(text)
    combined_text = "\n\n".join(pages_text)

print(f"📝 Extracted {len(combined_text)} chars")

# Pattern discovery prompt - we want RULES, not code
PROMPT = '''Analizza questo estratto conto bancario e identifica i PATTERN delle transazioni.

Per ogni TIPO di transazione (acquisto, vendita, deposito, dividendo, ecc.) dimmi:

1. KEYWORD: Quale parola identifica questo tipo di transazione?
2. RIGHE: Quante righe occupa una transazione di questo tipo?
3. STRUTTURA: Cosa contiene ogni riga?

Esempio di formato risposta:

TIPO: Acquisto
- KEYWORD: "Contrattazione" + "Acquista"
- RIGHE: 4
- STRUTTURA:
  - Riga 1: "Contrattazione {NomeProdotto} Acquista{Quantità}@{Prezzo}{Valuta} {Importo}"
  - Riga 2: "Commissione Valorenegoziato Costodiconversionevaluta Costototale"
  - Riga 3: "{Commissione}EUR {ValoreNegoziato}EUR ..."
  - Riga 4: "Tassodiconversione IDcontrattazione ISIN"
  - Riga 5: "{Tasso} {ID} {ISIN}"

TIPO: Deposito
- KEYWORD: "Trasferimentodiliquidità" + "Deposito"
- RIGHE: 3
- STRUTTURA:
  - Riga 1: "Trasferimentodiliquidità Deposito {Importo}"
  - Riga 2: "Commento DepositType ..."
  - Riga 3: ...

Ora analizza il seguente testo e elenca TUTTI i tipi di transazione con i loro pattern:

TESTO PDF:
''' + combined_text + '''

Rispondi SOLO con l'elenco dei pattern, niente codice.
'''

print(f"\n📤 Sending pattern discovery prompt to Qwen...")
print(f"   Prompt: {len(PROMPT)} chars (~{len(PROMPT)//4} tokens)")

print("\n" + "="*60)
print("IL PROMPT:")
print("="*60)
print(PROMPT[:1500])
print("\n... [seguito dal testo PDF]")
print("="*60)

input("\nPremi ENTER per inviare a Qwen...")

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 3000}
    },
    timeout=300
)

result = response.json().get("response", "")
print(f"\n📥 Received {len(result)} chars")

# Save
out_path = Path("data/extracted/transaction_patterns.md")
out_path.write_text(result, encoding='utf-8')
print(f"💾 Saved to: {out_path}")

print("\n" + "="*60)
print("PATTERN IDENTIFICATI:")
print("="*60)
print(result)
