"""
Phase 1 v3: Pure Pattern Discovery Prompt

Improvements:
- NO biased examples or pre-defined regex structures
- Strict JSON output request
- 10 sequential pages analysis
"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (First 10 pages)
pages_text = []
with pdfplumber.open(pdf_path) as pdf:
    for i in range(10): # Pages 0-9 
        if i < len(pdf.pages):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(f"--- PAGE {i+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Pure Discovery Prompt
PROMPT = f'''You are a Data Extraction Expert.
Your task is to analyze the bank statement text below and discover the transaction patterns.

GOAL:
Identify all different transaction types (trades, deposits, fees, etc.) and create a Regex Rule for each one.

OUTPUT:
Return a JSON object with the following structure. Do NOT include any explanations.

{{
  "patterns": [
    {{
      "transaction_type": "Name of the type (e.g. BUY, SELL, DEPOSIT)",
      "trigger_keyword": "A unique word that marks the start of this transaction",
      "regex_pattern": "A generic Python regex to capture the main data (amount, name, etc.)",
      "captured_fields": ["list", "of", "field", "names"]
    }}
  ]
}}

INSTRUCTIONS:
1. Look at the text samples.
2. Find repeating structures.
3. Write GENERIC regexes (use \d+ for numbers, .*? for text).
4. Do NOT match specific company names (e.g. use generic patterns).

PDF TEXT SAMPLES:
{sample_text}
'''

# 3. Print for Review
print("="*80)
print("PROPOSED PURE DISCOVERY PROMPT:")
print("="*80)
print(PROMPT[:1000] + "\n... [PDF TEXT CONTINUES] ...")
print("="*80)
print("\nWaiting for user approval to execute...")
