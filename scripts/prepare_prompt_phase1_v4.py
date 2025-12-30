"""
Phase 1 v4: Sandwich Prompt Strategy

Improvements:
- Sandwich Strategy: Instructions at START and END.
- Reduced Sample: 5 dense pages (start + end) to keep context manageable.
- Strict Parsing: Ask for JSON without markdown code blocks if possible.
"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (Dense pages: 0, 1, 2, 81, 82)
pages_to_extract = [0, 1, 2, 81, 82]
pages_text = []

with pdfplumber.open(pdf_path) as pdf:
    for p in pages_to_extract:
        if p < len(pdf.pages):
            text = pdf.pages[p].extract_text() or ""
            pages_text.append(f"--- PAGE {p+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Sandwich Prompt
PROMPT = f'''You are a Data Extraction Expert.
Your task is to analyze the bank statement text and generate Regex Rules in JSON format.
DO NOT WRITE A SUMMARY. WRITE ONLY JSON.

TARGET STRUCTURE:
{{
  "patterns": [
    {{
      "type": "BUY/SELL/DEPOSIT",
      "regex": "python regex pattern",
      "fields": ["amount", "currency", "etc"]
    }}
  ]
}}

PDF TEXT START:
{sample_text}
PDF TEXT END.

--------------------------------------------------------------------------------
CRITICAL INSTRUCTION:
Based on the text above, generate the JSON object defined in the TARGET STRUCTURE.
- Return ONLY valid JSON.
- No Markdown.
- No Explanations.
- No Summary.
- Start with {{ and end with }}.
--------------------------------------------------------------------------------
'''

# 3. Print for Review
print("="*80)
print("PROPOSED SANDWICH PROMPT V4:")
print("="*80)
print(PROMPT[:1000] + "\n... [PDF TEXT] ...\n" + PROMPT[-500:])
print("="*80)
print("\nWaiting for user approval to execute...")
