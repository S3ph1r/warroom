"""
Phase 1: Pattern Discovery Prompt Proposal

Goal: Ask Qwen to analyze PDF text and output Regex/Extraction Rules in JSON.
This script prepares and prints the prompt for User Review.
"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (First 3 pages are enough to see patterns)
pages_text = []
with pdfplumber.open(pdf_path) as pdf:
    # Pages 2, 83 contain Trades and Deposits - good variety
    for p in [1, 82]: # 0-indexed, so page 2 and 83
        text = pdf.pages[p].extract_text() or ""
        pages_text.append(f"--- PAGE SAMPLE ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Prompt
PROMPT = f'''You are a Data Extraction Expert. 
Your goal is to analyze the unstructured text from a Bank Statement PDF and define REGEX PATTERNS to extract transaction data.

We need to extract 4 types of transactions:
1. BUY (Acquisto)
2. SELL (Vendita)
3. DEPOSIT (Deposito)
4. DIVIDEND (Dividendo)

Analyze the provided TEXT SAMPLES and generate a JSON configuration with Regex patterns for each type.

The JSON structure must be exactly like this:
{{
  "common_patterns": {{
      "date": "regex to matches dates (e.g., 28-nov-2024)",
      "isin": "regex to match ISIN (e.g., US1234567890)"
  }},
  "transactions": [
    {{
      "type": "BUY",
      "start_keyword": "keyword that starts the line (e.g. Contrattazione)",
      "contains_keyword": "keyword that distinguishes this type (e.g. Acquista)",
      "regex": "regex capturing groups: name, quantity, price, currency",
      "field_map": {{ "1": "name", "2": "quantity", "3": "price", "4": "currency" }}
    }},
    {{
      "type": "SELL",
      "start_keyword": "...",
        "contains_keyword": "...",
       "regex": "...",
      "field_map": {{ ... }}
    }},
     {{
      "type": "DEPOSIT",
      "start_keyword": "...",
       "contains_keyword": "...",
      "regex": "...",
      "field_map": {{ ... }}
    }}
  ]
}}

TEXT SAMPLES:
{sample_text}

IMPORTANT: 
- Return ONLY the valid JSON.
- Regex must be Python compatible.
- Handle flexible whitespace with \s+
'''

# 3. Print for Review
print("="*80)
print("PROPOSED PROMPT FOR QWEN:")
print("="*80)
print(PROMPT)
print("="*80)
print("\nWaiting for user approval to execute...")
