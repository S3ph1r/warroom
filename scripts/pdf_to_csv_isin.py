"""
PDF to CSV with ISIN extraction

Strategy: Process pages collecting multi-line transaction blocks
Each transaction has:
- Main line: Contrattazione + name + Acquista/Vendi + qty@price
- Detail lines: Commissione, Valorenegoziato, ISIN, etc.
"""
import pdfplumber
import pandas as pd
import re
from pathlib import Path

MONTHS_IT = {
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
    'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}

def parse_italian_date(text):
    match = re.match(r'(\d{1,2})-([a-z]{3})-(\d{4})', text.lower())
    if match:
        day, month_it, year = match.groups()
        month = MONTHS_IT.get(month_it, '01')
        return f"{year}-{month}-{int(day):02d}"
    return None

def parse_amount(text):
    if not text:
        return 0.0
    clean = text.replace('.', '').replace(',', '.').replace('-', '')
    try:
        return float(clean)
    except:
        return 0.0

def extract_isin(text):
    """Extract ISIN code from text. ISIN = 2 letters + 10 alphanumeric."""
    match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', text)
    return match.group(1) if match else None

def extract_transactions(pdf_path):
    transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        # Get ALL text from PDF first
        all_lines = []
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for line in text.split('\n'):
                all_lines.append({'page': page_num, 'text': line.strip()})
        
        print(f"📝 Total lines: {len(all_lines)}")
        
        current_date = None
        i = 0
        
        while i < len(all_lines):
            line = all_lines[i]['text']
            page_num = all_lines[i]['page']
            
            # Date detection
            date_match = re.match(r'^(\d{1,2}-[a-z]{3}-\d{4})', line.lower())
            if date_match:
                current_date = parse_italian_date(date_match.group(1))
                i += 1
                continue
            
            # Contrattazione (Trade) - collect next 5 lines for ISIN
            if line.startswith('Contrattazione'):
                block = line
                for j in range(1, 6):
                    if i + j < len(all_lines):
                        block += " " + all_lines[i + j]['text']
                
                # Extract ISIN from block
                isin = extract_isin(block)
                
                # BUY pattern
                buy_match = re.search(
                    r'Contrattazione\s+(.+?)\s+Acquista\s*(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?',
                    line
                )
                # SELL pattern
                sell_match = re.search(
                    r'Contrattazione\s+(.+?)\s+Vendi\s*-?(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?',
                    line
                )
                
                if buy_match or sell_match:
                    match = buy_match or sell_match
                    operation = 'BUY' if buy_match else 'SELL'
                    
                    transactions.append({
                        'page': page_num,
                        'date': current_date,
                        'type': 'Contrattazione',
                        'operation': operation,
                        'name': match.group(1).strip()[:60],
                        'isin': isin,
                        'quantity': float(match.group(2)),
                        'price': parse_amount(match.group(3)),
                        'currency': (match.group(4) or 'EUR'),
                    })
                
                i += 5  # Skip detail lines
                continue
            
            # Trasferimento (Deposit/Withdraw)
            if 'Trasferimentodiliquidit' in line:
                if 'Deposito' in line:
                    amount_match = re.search(r'Deposito\s+([\d.,]+)', line)
                    if amount_match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'Trasferimento',
                            'operation': 'DEPOSIT',
                            'name': 'Cash Deposit',
                            'isin': None,
                            'quantity': 1,
                            'price': parse_amount(amount_match.group(1)),
                            'currency': 'EUR',
                        })
                elif 'Prelievo' in line:
                    amount_match = re.search(r'Prelievo\s+([\d.,]+)', line)
                    if amount_match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'Trasferimento',
                            'operation': 'WITHDRAW',
                            'name': 'Cash Withdraw',
                            'isin': None,
                            'quantity': 1,
                            'price': parse_amount(amount_match.group(1)),
                            'currency': 'EUR',
                        })
            
            # VenditaAllachiusura (Corporate sell)
            if 'VenditaAllachiusura' in line:
                # Collect next lines for ISIN
                block = line
                for j in range(1, 3):
                    if i + j < len(all_lines):
                        block += " " + all_lines[i + j]['text']
                isin = extract_isin(block)
                
                match = re.search(r'VenditaAllachiusura\s*-?(\d+)\s*@\s*([\d.,]+)', line)
                if match:
                    transactions.append({
                        'page': page_num,
                        'date': current_date,
                        'type': 'CorporateEvent',
                        'operation': 'SELL',
                        'name': 'Corporate Event Sale',
                        'isin': isin,
                        'quantity': float(match.group(1)),
                        'price': parse_amount(match.group(2)),
                        'currency': 'EUR',
                    })
            
            # AcquistoInapertura (Corporate buy)
            if 'AcquistoInapertura' in line:
                block = line
                for j in range(1, 3):
                    if i + j < len(all_lines):
                        block += " " + all_lines[i + j]['text']
                isin = extract_isin(block)
                
                match = re.search(r'AcquistoInapertura\s*(\d+)\s*@\s*([\d.,]+)', line)
                if match:
                    transactions.append({
                        'page': page_num,
                        'date': current_date,
                        'type': 'CorporateEvent',
                        'operation': 'BUY',
                        'name': 'Corporate Event Buy',
                        'isin': isin,
                        'quantity': float(match.group(1)),
                        'price': parse_amount(match.group(2)),
                        'currency': 'EUR',
                    })
            
            # Operazionesulcapitale (Corporate Actions - stock splits, distributions)
            if 'Operazionesulcapitale' in line:
                block = line
                for j in range(1, 4):
                    if i + j < len(all_lines):
                        block += " " + all_lines[i + j]['text']
                isin = extract_isin(block)
                
                # Distribution of shares
                if 'Distribuzionetitoliintermedi' in line or 'CorporateActions-ShareAmount' in block:
                    # Try to find share amount
                    share_match = re.search(r'CorporateActions-ShareAmount\s+\S+\s+(\d+)', block)
                    if share_match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'CorporateAction',
                            'operation': 'DISTRIBUTION',
                            'name': 'Share Distribution',
                            'isin': isin,
                            'quantity': float(share_match.group(1)),
                            'price': 0,
                            'currency': 'EUR',
                        })
                
                # Reverse stock split
                if 'Frazionamentoazionarioinverso' in line:
                    transactions.append({
                        'page': page_num,
                        'date': current_date,
                        'type': 'CorporateAction',
                        'operation': 'REVERSE_SPLIT',
                        'name': 'Reverse Stock Split',
                        'isin': isin,
                        'quantity': 0,
                        'price': 0,
                        'currency': 'EUR',
                    })
            
            i += 1
    
    return transactions


def main():
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    print("🔄 PDF to CSV with ISIN Extraction")
    print("=" * 60)
    
    transactions = extract_transactions(str(pdf_path))
    
    print(f"\n📊 Extracted {len(transactions)} transactions")
    
    df = pd.DataFrame(transactions)
    
    if len(df) > 0:
        print("\nOperations breakdown:")
        print(df['operation'].value_counts().to_string())
        
        print(f"\nISIN coverage: {df['isin'].notna().sum()}/{len(df)} ({100*df['isin'].notna().mean():.0f}%)")
        
        print("\nSample with ISIN:")
        print(df[df['isin'].notna()][['date', 'operation', 'name', 'isin', 'quantity']].head(10).to_string())
        
        # Save
        csv_path = Path("data/extracted/BG_SAXO_Transactions_ISIN.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved to: {csv_path}")
        
        xlsx_path = Path("data/extracted/BG_SAXO_Transactions_ISIN.xlsx")
        df.to_excel(xlsx_path, index=False)
        print(f"💾 Saved to: {xlsx_path}")


if __name__ == "__main__":
    main()
