"""
Phase 1 v2: Pattern Discovery Prompt - Proposal

Improvements:
- Sample: 10 sequential pages (1-10)
- Prompt: Generic instructions, NO biased examples
- Output: Strict JSON request
"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (First 10 pages)
pages_text = []
with pdfplumber.open(pdf_path) as pdf:
    for i in range(10): # Pages 0-9 (first 10)
        if i < len(pdf.pages):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(f"--- PAGE {i+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Prompt
PROMPT = f'''You are a Data Extraction Expert.
Your task is to analyze the Bank Statement PDF text and defining generic REGEX patterns to extract transactions.

TARGET: Extract 4 transaction types:
1. BUY
2. SELL
3. DEPOSIT
4. DIVIDEND

OUTPUT FORMAT:
Return a JSON object containing the regex rules. Do not include any explanation or markdown.
Use Python-compatible naming for named groups (e.g. (?P<name>...)).

JSON STRUCTURE:
{{
  "common": {{
      "date_regex": "regex for date (DD-mmm-YYYY)",
      "isin_regex": "regex for ISIN code"
  }},
  "rules": [
    {{
      "type": "BUY",
      "keyword": "unique text that identifies this transaction",
      "regex": "regex with named groups: name, quantity, price"
    }},
    {{
      "type": "SELL",
      "keyword": "unique text that identifies this transaction",
      "regex": "regex with named groups: name, quantity, price"
    }},
    {{
      "type": "DEPOSIT",
      "keyword": "unique text that identifies this transaction",
      "regex": "regex with named groups: amount"
    }}
  ]
}}

INSTRUCTIONS:
- Regex must be GENERIC. Do not hardcode company names (e.g. use .*? instead of "Alphabet").
- Handle flexible whitespace with \s+

PDF TEXT SAMPLES:
{sample_text}
'''

# 3. Print for Review
print("="*80)
print("PROPOSED PROMPT (First 500 chars + Instructions):")
print("="*80)
print(PROMPT[:1500] + "\n... [PDF TEXT CONTINUES] ...")
print("="*80)
print("\nWaiting for user approval to execute...")
