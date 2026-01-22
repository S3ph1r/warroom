"""
Minimal Prompt - Let Qwen figure out the patterns

Super simple instructions, no detailed examples.
Just tell Qwen what we need and let it analyze the text.
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

# MINIMAL prompt - simple instructions only
PROMPT = '''Questo è il testo estratto da un PDF di un estratto conto bancario BG SAXO.

Scrivi un parser Python con pdfplumber che estrae tutte le transazioni (acquisti, vendite, depositi, dividendi).

Per ogni transazione estrai: data, tipo operazione, nome asset, ISIN, quantità, prezzo, valuta.

Testo PDF:

''' + combined_text + '''

Rispondi solo con il codice Python completo.
'''

print(f"\n📤 Sending minimal prompt to Qwen...")
print(f"   Prompt: {len(PROMPT)} chars (~{len(PROMPT)//4} tokens)")

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 5000}
    },
    timeout=300
)

result = response.json().get("response", "")
print(f"\n📥 Received {len(result)} chars")

# Save
out_path = Path("data/extracted/llm_parser_minimal.py")
out_path.write_text(result, encoding='utf-8')
print(f"💾 Saved to: {out_path}")

print("\n" + "="*60)
print("GENERATED CODE:")
print("="*60)
print(result[:4000])
