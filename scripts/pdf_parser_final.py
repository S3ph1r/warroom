"""
LLM-Generated Parser - Fixed Version
Based on Qwen's analysis of 5 sample pages
"""
import re
import pdfplumber
import pandas as pd
from pathlib import Path

# Global patterns
DATE_PATTERN = re.compile(r'(\d{1,2}-[a-z]{3}-\d{4})', re.IGNORECASE)
ISIN_PATTERN = re.compile(r'([A-Z]{2}[A-Z0-9]{10})')

# Italian months
MONTHS_IT = {'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06',
             'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'}

def convert_date(date_str):
    """Convert 28-nov-2024 to 2024-11-28"""
    match = re.match(r'(\d{1,2})-([a-z]{3})-(\d{4})', date_str.lower())
    if match:
        d, m, y = match.groups()
        return f"{y}-{MONTHS_IT.get(m, '01')}-{int(d):02d}"
    return date_str

def parse_amount(text):
    """Parse 1.234,56 to 1234.56"""
    if not text:
        return 0.0
    clean = text.replace('.', '').replace(',', '.').replace('-', '').strip()
    try:
        return float(clean)
    except:
        return 0.0

def extract_isin(text):
    """Extract ISIN from text"""
    match = ISIN_PATTERN.search(text)
    return match.group(1) if match else None


def parse_bgsaxo_pdf(pdf_path: str) -> list:
    """
    Parse BG SAXO transactions PDF.
    Handles: BUY, SELL, DEPOSIT, WITHDRAW, REVERSE_SPLIT, DISTRIBUTION
    """
    transactions = []
    current_date = None
    
    with pdfplumber.open(pdf_path) as pdf:
        # Get all lines with page info
        all_lines = []
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for line in text.split('\n'):
                if line.strip():
                    all_lines.append({'page': page_num, 'text': line.strip()})
        
        print(f"📝 Total lines: {len(all_lines)}")
        
        i = 0
        while i < len(all_lines):
            line = all_lines[i]['text']
            page = all_lines[i]['page']
            
            # Collect next 5 lines for context
            block = line
            for j in range(1, 6):
                if i + j < len(all_lines):
                    block += "\n" + all_lines[i + j]['text']
            
            # Date detection
            date_match = DATE_PATTERN.match(line)
            if date_match:
                current_date = convert_date(date_match.group(1))
                i += 1
                continue
            
            # BUY: Contrattazione ... Acquista X@Y
            if 'Contrattazione' in line and 'Acquista' in line:
                match = re.search(r'Contrattazione\s+(.+?)\s+Acquista\s*(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?', line)
                if match:
                    isin = extract_isin(block)
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'BUY',
                        'name': match.group(1).strip()[:60],
                        'isin': isin,
                        'quantity': float(match.group(2)),
                        'price': parse_amount(match.group(3)),
                        'currency': match.group(4) or 'EUR'
                    })
                i += 5
                continue
            
            # SELL: Contrattazione ... Vendi X@Y
            if 'Contrattazione' in line and 'Vendi' in line:
                match = re.search(r'Contrattazione\s+(.+?)\s+Vendi\s*-?(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?', line)
                if match:
                    isin = extract_isin(block)
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'SELL',
                        'name': match.group(1).strip()[:60],
                        'isin': isin,
                        'quantity': float(match.group(2)),
                        'price': parse_amount(match.group(3)),
                        'currency': match.group(4) or 'EUR'
                    })
                i += 5
                continue
            
            # DEPOSIT: Trasferimentodiliquidità Deposito
            if 'Trasferimentodiliquidit' in line and 'Deposito' in line:
                match = re.search(r'Deposito\s+([\d.,]+)', line)
                if match:
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'DEPOSIT',
                        'name': 'Cash Deposit',
                        'isin': None,
                        'quantity': 1,
                        'price': parse_amount(match.group(1)),
                        'currency': 'EUR'
                    })
                i += 1
                continue
            
            # WITHDRAW: Trasferimentodiliquidità Prelievo
            if 'Trasferimentodiliquidit' in line and 'Prelievo' in line:
                match = re.search(r'Prelievo\s+([\d.,]+)', line)
                if match:
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'WITHDRAW',
                        'name': 'Cash Withdraw',
                        'isin': None,
                        'quantity': 1,
                        'price': parse_amount(match.group(1)),
                        'currency': 'EUR'
                    })
                i += 1
                continue
            
            # Corporate Actions
            if 'Operazionesulcapitale' in line:
                isin = extract_isin(block)
                
                # Reverse Split
                if 'Frazionamentoazionarioinverso' in block:
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'REVERSE_SPLIT',
                        'name': 'Reverse Stock Split',
                        'isin': isin,
                        'quantity': 0,
                        'price': 0,
                        'currency': 'EUR'
                    })
                # Distribution
                elif 'Distribuzionetitoliintermedi' in block or 'CorporateActions-ShareAmount' in block:
                    share_match = re.search(r'CorporateActions-ShareAmount\s+\S+\s+(\d+)', block)
                    qty = float(share_match.group(1)) if share_match else 0
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'DISTRIBUTION',
                        'name': 'Share Distribution',
                        'isin': isin,
                        'quantity': qty,
                        'price': 0,
                        'currency': 'EUR'
                    })
                
                i += 4
                continue
            
            # VenditaAllachiusura (Corporate sell)
            if 'VenditaAllachiusura' in line:
                match = re.search(r'VenditaAllachiusura\s*-?(\d+)\s*@\s*([\d.,]+)', line)
                if match:
                    isin = extract_isin(block)
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'SELL',
                        'name': 'Corporate Event Sale',
                        'isin': isin,
                        'quantity': float(match.group(1)),
                        'price': parse_amount(match.group(2)),
                        'currency': 'EUR'
                    })
                i += 1
                continue
            
            # AcquistoInapertura (Corporate buy)
            if 'AcquistoInapertura' in line:
                match = re.search(r'AcquistoInapertura\s*(\d+)\s*@\s*([\d.,]+)', line)
                if match:
                    isin = extract_isin(block)
                    transactions.append({
                        'page': page,
                        'date': current_date,
                        'operation': 'BUY',
                        'name': 'Corporate Event Buy',
                        'isin': isin,
                        'quantity': float(match.group(1)),
                        'price': parse_amount(match.group(2)),
                        'currency': 'EUR'
                    })
                i += 1
                continue
            
            i += 1
    
    return transactions


def main():
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    print("🔄 PDF Parser (LLM-Generated + Fixed)")
    print("=" * 60)
    
    transactions = parse_bgsaxo_pdf(str(pdf_path))
    
    print(f"\n📊 Extracted {len(transactions)} transactions")
    
    df = pd.DataFrame(transactions)
    
    if len(df) > 0:
        print("\nOperations breakdown:")
        print(df['operation'].value_counts().to_string())
        
        print(f"\nISIN coverage: {df['isin'].notna().sum()}/{len(df)} ({100*df['isin'].notna().mean():.0f}%)")
        
        print("\nSample with ISIN:")
        print(df[df['isin'].notna()][['date', 'operation', 'name', 'isin', 'quantity']].head(10).to_string())
        
        # Save
        csv_path = Path("data/extracted/BG_SAXO_Transactions_Final.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved to: {csv_path}")


if __name__ == "__main__":
    main()
