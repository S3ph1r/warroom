"""Test Page 83 (deposit) with new prompt"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_bgsaxo_transactions import PROMPT_TRANSACTIONS, call_ollama
import pdfplumber
import json
import re

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# Extract page 83 (index 82)
with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[82].extract_text()
    print(f"Page 83 text ({len(text)} chars):")
    print("="*50)
    print(text)
    print("="*50)

# Call LLM
prompt = PROMPT_TRANSACTIONS.format(content=text)
print("\n📤 Calling LLM...")
response = call_ollama(prompt, "P83")

print(f"\n📥 Response ({len(response) if response else 0} chars):")
print("="*50)

if response:
    # Parse JSON
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        try:
            result = json.loads(match.group())
            print(json.dumps(result, indent=2))
        except:
            print("Parse error - raw response:")
            print(response[:500])
    else:
        print("No JSON found - raw response:")
        print(response[:500])
else:
    print("No response!")
