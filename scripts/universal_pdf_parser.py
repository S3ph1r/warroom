"""
Universal PDF Parser Engine (Final Version)

This script implements the "Parser Factory" pattern.
It takes the concepts discovered by the AI (Keywords, Structures) and implements them in a robust, deterministic engine.

FEATURES:
- Context Awareness: Looks ahead 5 lines for ISINs.
- Multi-Pattern Support: Handles Buy, Sell, Deposit, Dividend, CorpActions.
- Robust Float Parsing: Handles Italian number formats (1.234,56).
- Validation: Checks ISIN coverage.
"""
import pdfplumber
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==============================================================================
# 1. ROBUST CONFIGURATION (Refined from AI suggestions)
# ==============================================================================
RULES = {
    "COMMON": {
        "date_fmt": r"(\d{1,2}-[a-z]{3}-\d{4})",  # 28-nov-2024
        "isin": r"([A-Z]{2}[A-Z0-9]{10})"          # US1234567890
    },
    "TRANSACTIONS": [
        {
            "type": "BUY",
            "trigger": "Contrattazione",
            "validate": "Acquista",
            # Improved Regex: Capture Name (lazy), Qty, Price, Currency (optional)
            "regex": r"Contrattazione\s+(?P<name>.*?)\s+Acquista\s*(?P<quantity>\d+)\s*@\s*(?P<price>[\d.,]+)\s*(?P<currency>[A-Z]{3})?",
            "context_lines": 5  # Look ahead 5 lines for ISIN
        },
        {
            "type": "SELL",
            "trigger": "Contrattazione",
            "validate": "Vendi",
            # Handle "Vendi-" or "Vendi "
            "regex": r"Contrattazione\s+(?P<name>.*?)\s+Vendi\s*-?(?P<quantity>\d+)\s*@\s*(?P<price>[\d.,]+)\s*(?P<currency>[A-Z]{3})?",
            "context_lines": 5
        },
        {
            "type": "DEPOSIT",
            "trigger": "Trasferimentodiliquidità",
            "validate": "Deposito",
            "regex": r"Trasferimentodiliquidità\s+Deposito\s+(?P<amount>[\d.,]+)",
            "context_lines": 2
        },
        {
             "type": "WITHDRAW",
             "trigger": "Trasferimentodiliquidità",
             "validate": "Prelievo",
             "regex": r"Trasferimentodiliquidità\s+Prelievo\s+(?P<amount>[\d.,]+)",
             "context_lines": 2
        },
        {
            "type": "DIVIDEND",
            "trigger": "Operazionesulcapitale",
            "validate": "Dividendoincontanti",
            "regex": r"Operazionesulcapitale\s+(?P<name>.*?)\s+Dividendoincontanti\s+(?P<amount>[\d.,]+)",
            "context_lines": 5
        },
        {
             "type": "CORP_ACTION", # Generic fallback for other corporate actions
             "trigger": "Operazionesulcapitale",
             "validate": None, # Validate if NOT dividend
             "regex": r"Operazionesulcapitale\s+(?P<name>.*?)\s+(?P<action>\w+)",
             "context_lines": 5
        },
        # Auto-Sell / Auto-Buy (from previous analysis)
        {
            "type": "AUTO_SELL",
            "trigger": "VenditaAllachiusura",
            "validate": None,
            "regex": r"(?P<name>.*?)\s+VenditaAllachiusura\s*-(?P<quantity>\d+)@\s*(?P<price>[\d.,]+)",
            "context_lines": 5
        },
         {
            "type": "AUTO_BUY",
            "trigger": "AcquistoInapertura",
            "validate": None,
            "regex": r"(?P<name>.*?)\s+AcquistoInapertura\s*(?P<quantity>\d+)@\s*(?P<price>[\d.,]+)",
            "context_lines": 5
        }
    ]
}

# Italian Month Map
MONTHS = {
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06',
    'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================
def parse_date(date_str):
    if not date_str: return None
    try:
        match = re.match(r"(\d+)-([a-z]+)-(\d+)", date_str.lower())
        if match:
            d, m, y = match.groups()
            return f"{y}-{MONTHS.get(m, '01')}-{int(d):02d}"
    except: pass
    return None

def parse_number(num_str):
    if not num_str: return 0.0
    # Italian format: 1.234,56 -> 1234.56
    clean = num_str.replace('.', '').replace(',', '.')
    try:
        return float(clean)
    except: return 0.0

def extract_context_data(lines, rule):
    """Scan subsequent lines for additional data like ISIN"""
    ctx_data = {}
    
    # Check for ISIN
    if "context_lines" in rule:
        combined_text = " ".join(lines) # Join context lines
        isin_match = re.search(RULES["COMMON"]["isin"], combined_text)
        if isin_match:
            ctx_data["isin"] = isin_match.group(1)
            
    return ctx_data

# ==============================================================================
# 3. PARSER ENGINE
# ==============================================================================
def parse_pdf(pdf_path):
    transactions = []
    current_date = None
    
    print(f"🚀 Starting extraction on: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"📄 Processing {total_pages} pages...")
        
        all_lines = []
        # Pre-load all lines with page numbering
        for p_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    all_lines.append( (p_idx+1, line.strip()) )
                    
        # Iterate lines
        i = 0
        while i < len(all_lines):
            page_num, line = all_lines[i]
            
            # 1. Update Current Date (Stateful)
            date_match = re.match(RULES["COMMON"]["date_fmt"], line.lower())
            if date_match:
                current_date = parse_date(date_match.group(1))
                i += 1
                continue
            
            # 2. Check Transaction Rules
            for rule in RULES["TRANSACTIONS"]:
                # Keyword Trigger check (fast)
                if rule["trigger"] in line:
                    if rule.get("validate") and rule["validate"] not in line:
                         continue # Secondary keyword missing
                    
                    # Regex Extraction (precise)
                    match = re.search(rule["regex"], line)
                    if match:
                        data = match.groupdict()
                        
                        # Extract Context Data (ISIN, etc)
                        context_window = []
                        for offset in range(1, rule.get("context_lines", 0)+1):
                            if i + offset < len(all_lines):
                                context_window.append(all_lines[i+offset][1])
                        
                        ctx_data = extract_context_data(context_window, rule)
                        
                        # Build Record
                        record = {
                            "date": current_date,
                            "type": rule["type"],
                            "raw_name": data.get("name", "").strip(),
                            "isin": ctx_data.get("isin"),
                            "quantity": parse_number(data.get("quantity")),
                            "price": parse_number(data.get("price") or data.get("amount")),
                            "currency": data.get("currency", "EUR"), # Default EUR
                            "page": page_num
                        }
                        transactions.append(record)
                        
                        # Skip context lines only if highly confident (optional, here we don't skip to be safe)
                        break # Stop checking other rules for this line
            
            i += 1
            
    return pd.DataFrame(transactions)

# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    pdf_file = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    df = parse_pdf(pdf_file)
    
    print("\n✅ Extraction Complete!")
    print(f"📊 Total Transactions: {len(df)}")
    print(f"TYPES:\n{df['type'].value_counts()}")
    
    # Validation Check
    valid_isin = df['isin'].notna().sum()
    print(f"\nISIN Coverage: {valid_isin}/{len(df)} ({valid_isin/len(df)*100:.1f}%)")
    
    # Save
    out_csv = Path("data/extracted/BG_SAXO_Transactions_FinalVersion.csv")
    df.to_csv(out_csv, index=False)
    print(f"💾 Saved to: {out_csv}")
    
    print("\nSAMPLE DATA (First 10):")
    print(df[['date', 'type', 'raw_name', 'quantity', 'price', 'isin']].head(10).to_string())
    
    print("\nSAMPLE DATA (Last 5):")
    print(df[['date', 'type', 'raw_name', 'quantity', 'price', 'isin']].tail(5).to_string())
