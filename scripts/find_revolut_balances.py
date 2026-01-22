
import fitz
from pathlib import Path
import re

pdf = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

def find_balance(text, currency):
    # Regex for "Saldo finale 10.123 XAU" or similar.
    # Pattern: "Saldo" ... number ... currency
    # Or "Balance" ...
    # Also look for just the currency and nearby numbers.
    lines = text.split('\n')
    print(f"--- {currency} SEARCH ---")
    for i, line in enumerate(lines):
        if currency in line:
            print(f"HIT: {line}")
            # print context
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                print(f"   {lines[j]}")

if pdf.exists():
    doc = fitz.open(pdf)
    
    # Page 2 (XAG?)
    page2 = doc[1]
    blocks2 = page2.get_text("blocks")
    blocks2.sort(key=lambda b: (b[1], b[0]))
    text2 = "\n".join([b[4] for b in blocks2])
    print("--- PAGE 2 TEXT ---")
    print(text2[:1000])
    find_balance(text2, "XAG")

    # Page 3 (XAU?)
    page3 = doc[2]
    blocks3 = page3.get_text("blocks")
    blocks3.sort(key=lambda b: (b[1], b[0]))
    text3 = "\n".join([b[4] for b in blocks3])
    print("\n--- PAGE 3 TEXT ---")
    print(text3[:1000])
    find_balance(text3, "XAU")
    
else:
    print("File not found")
