"""
BG SAXO Transaction PDF Parser - Pure Python
Generated with LLM-assisted structure analysis

Strategy:
1. Extract ALL text from PDF as single document
2. Use regex patterns to identify:
   - Date separators (DD-mmm-YYYY)
   - Transaction blocks (Contrattazione, Trasferimento)
   - Detail rows (ISIN, Commissione, etc.)
3. State machine to track current date and transaction context
"""

import re
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import pdfplumber
import json

# Italian month mapping
MONTHS_IT = {
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
    'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}


def parse_italian_date(date_str: str) -> Optional[str]:
    """Parse Italian date format like '28-nov-2024' to 'YYYY-MM-DD'."""
    match = re.match(r'(\d{1,2})-([a-z]{3})-(\d{4})', date_str.lower())
    if match:
        day, month_it, year = match.groups()
        month = MONTHS_IT.get(month_it, '01')
        return f"{year}-{month}-{int(day):02d}"
    return None


def parse_amount(amount_str: str) -> float:
    """Parse Italian formatted amount (1.234,56 -> 1234.56)."""
    if not amount_str:
        return 0.0
    # Remove thousands separator, convert decimal separator
    clean = amount_str.replace('.', '').replace(',', '.')
    try:
        return float(clean)
    except:
        return 0.0


def extract_transaction_details(text_block: str) -> Dict:
    """Extract details from a transaction text block."""
    details = {
        'isin': None,
        'fees': 0.0,
        'exchange_rate': 1.0,
        'trade_id': None
    }
    
    # ISIN pattern (US..., IT..., IE..., etc.)
    isin_match = re.search(r'ISIN\s*([A-Z]{2}[A-Z0-9]{10})', text_block)
    if isin_match:
        details['isin'] = isin_match.group(1)
    else:
        # Try standalone ISIN pattern
        isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', text_block)
        if isin_match:
            details['isin'] = isin_match.group(1)
    
    # Commissione (fees) pattern
    fee_match = re.search(r'Commissione\s*(-?[\d.,]+)\s*EUR', text_block)
    if fee_match:
        details['fees'] = abs(parse_amount(fee_match.group(1)))
    
    # Exchange rate
    rate_match = re.search(r'Tassodiconversione\s*([\d.,]+)', text_block)
    if rate_match:
        details['exchange_rate'] = parse_amount(rate_match.group(1))
    
    # Trade ID
    id_match = re.search(r'IDcontrattazione\s*(\d+)', text_block)
    if id_match:
        details['trade_id'] = id_match.group(1)
    
    return details


def parse_bgsaxo_transactions_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse BG SAXO transactions PDF using pattern-based extraction.
    
    Returns a list of transaction dictionaries with:
    - date, operation, ticker, isin, name, quantity, price, 
    - total_amount, currency, fees
    """
    transactions = []
    
    # Extract all text from PDF
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_text += text + "\n"
    
    print(f"📄 Extracted {len(all_text)} characters from PDF")
    
    # State tracking
    current_date = None
    lines = all_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for date separator (e.g., "28-nov-2024")
        date_match = re.match(r'^(\d{1,2}-[a-z]{3}-\d{4})', line.lower())
        if date_match:
            current_date = parse_italian_date(date_match.group(1))
            i += 1
            continue
        
        # Check for "Contrattazione" (trade)
        if line.startswith('Contrattazione'):
            # Collect the transaction block (next ~5 lines for details)
            block_lines = [line]
            for j in range(1, 6):
                if i + j < len(lines):
                    block_lines.append(lines[i + j])
            block_text = '\n'.join(block_lines)
            
            # Patterns for BUY: "Acquista2@301,93" or "Acquista 2@301,93"
            # Patterns for SELL: "Vendi-2@297,89USD" (negative quantity)
            
            # Try BUY pattern: Acquista followed by qty@price
            buy_match = re.search(
                r'Contrattazione\s+(.+?)\s+Acquista\s*(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?',
                line, re.IGNORECASE
            )
            
            # Try SELL pattern: Vendi followed by -qty@price  
            sell_match = re.search(
                r'Contrattazione\s+(.+?)\s+Vendi\s*-?(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?',
                line, re.IGNORECASE
            )
            
            if buy_match or sell_match:
                match = buy_match or sell_match
                operation = 'BUY' if buy_match else 'SELL'
                
                asset_name = match.group(1).strip()
                quantity = float(match.group(2))
                price = parse_amount(match.group(3))
                currency = (match.group(4) or 'EUR').upper()
                
                # Get additional details from block
                details = extract_transaction_details(block_text)
                
                # Try to extract ticker from asset name
                ticker = None
                ticker_match = re.search(r'\*\*See\s*([A-Z]+:[a-z]+)', asset_name)
                if ticker_match:
                    ticker = ticker_match.group(1)
                # Also check for pattern like "**SeeWMT:xnas"
                ticker_match2 = re.search(r'\*\*See([A-Z]+:[a-z]+)', asset_name)
                if ticker_match2:
                    ticker = ticker_match2.group(1)
                
                txn = {
                    'date': current_date or datetime.now().strftime('%Y-%m-%d'),
                    'operation': operation,
                    'ticker': ticker,
                    'isin': details['isin'],
                    'name': asset_name[:80],
                    'quantity': quantity,
                    'price': price,
                    'total_amount': quantity * price,
                    'currency': currency,
                    'fees': details['fees']
                }
                transactions.append(txn)
            
            i += 5  # Skip detail lines
            continue
        
        # Check for "VenditaAllachiusura" (sell at close - corporate events)
        if 'VenditaAllachiusura' in line:
            sell_match = re.search(r'VenditaAllachiusura\s*-?(\d+)\s*@\s*([\d.,]+)', line)
            if sell_match:
                quantity = float(sell_match.group(1))
                price = parse_amount(sell_match.group(2))
                
                # Look for ISIN in same line
                isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', line)
                isin = isin_match.group(1) if isin_match else None
                
                txn = {
                    'date': current_date or datetime.now().strftime('%Y-%m-%d'),
                    'operation': 'SELL',
                    'ticker': None,
                    'isin': isin,
                    'name': 'Corporate Event Sale',
                    'quantity': quantity,
                    'price': price,
                    'total_amount': quantity * price,
                    'currency': 'EUR',
                    'fees': 0
                }
                transactions.append(txn)
            i += 1
            continue
        
        # Check for "AcquistoInapertura" (buy at open - corporate events)
        if 'AcquistoInapertura' in line:
            buy_match = re.search(r'AcquistoInapertura\s*(\d+)\s*@\s*([\d.,]+)', line)
            if buy_match:
                quantity = float(buy_match.group(1))
                price = parse_amount(buy_match.group(2))
                
                isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', line)
                isin = isin_match.group(1) if isin_match else None
                
                txn = {
                    'date': current_date or datetime.now().strftime('%Y-%m-%d'),
                    'operation': 'BUY',
                    'ticker': None,
                    'isin': isin,
                    'name': 'Corporate Event Buy',
                    'quantity': quantity,
                    'price': price,
                    'total_amount': quantity * price,
                    'currency': 'EUR',
                    'fees': 0
                }
                transactions.append(txn)
            i += 1
            continue
        
        # Check for "Trasferimento di liquidità" (cash transfer)
        if 'Trasferimento' in line and 'liquidit' in line.lower():
            # Next line should have operation type
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                if 'Deposito' in next_line:
                    operation = 'DEPOSIT'
                elif 'Prelievo' in next_line:
                    operation = 'WITHDRAW'
                else:
                    i += 1
                    continue
                
                # Look for amount
                amount_match = re.search(r'([\d.,]+)\s*EUR', next_line)
                if not amount_match:
                    # Try subsequent lines
                    for j in range(2, 5):
                        if i + j < len(lines):
                            amount_match = re.search(r'([\d.,]+)\s*EUR', lines[i + j])
                            if amount_match:
                                break
                
                if amount_match:
                    amount = parse_amount(amount_match.group(1))
                    txn = {
                        'date': current_date or datetime.now().strftime('%Y-%m-%d'),
                        'operation': operation,
                        'ticker': 'CASH:EUR',
                        'isin': None,
                        'name': f'Cash {operation.title()}',
                        'quantity': 1,
                        'price': amount,
                        'total_amount': amount,
                        'currency': 'EUR',
                        'fees': 0
                    }
                    transactions.append(txn)
            
            i += 3
            continue
        
        # Check for "Dividendo" (dividend)
        if 'Dividendo' in line:
            # Extract dividend details
            amount_match = re.search(r'([\d.,]+)\s*(USD|EUR)', line)
            if amount_match:
                amount = parse_amount(amount_match.group(1))
                currency = amount_match.group(2)
                txn = {
                    'date': current_date or datetime.now().strftime('%Y-%m-%d'),
                    'operation': 'DIVIDEND',
                    'ticker': None,
                    'isin': None,
                    'name': 'Dividend',
                    'quantity': 1,
                    'price': amount,
                    'total_amount': amount,
                    'currency': currency,
                    'fees': 0
                }
                transactions.append(txn)
            i += 1
            continue
        
        i += 1
    
    return transactions


def main():
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Parsing: {pdf_path.name}")
    print()
    
    transactions = parse_bgsaxo_transactions_pdf(str(pdf_path))
    
    print(f"\n📊 Extracted {len(transactions)} transactions")
    
    # Operations breakdown
    from collections import Counter
    ops = Counter(t['operation'] for t in transactions)
    print("\nOperations:")
    for op, count in ops.most_common():
        print(f"  {op}: {count}")
    
    # Sample transactions
    print("\nSample transactions:")
    for t in transactions[:10]:
        print(f"  {t['date']}: {t['operation']} {t['quantity']} x {t['ticker'] or t['name'][:20]}")
    
    # Save to JSON
    out_path = Path(__file__).parent.parent / "data" / "extracted" / "BG_SAXO_Transactions_Python.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'transactions': transactions}, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to: {out_path}")


if __name__ == "__main__":
    main()
