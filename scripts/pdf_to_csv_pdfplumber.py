"""
PDF to CSV using pdfplumber - line-by-line structured extraction

Since the PDF doesn't have true tables, we parse the text
structure to identify transactions and build a clean dataset.
"""
import pdfplumber
import pandas as pd
import re
from pathlib import Path
from datetime import datetime

# Italian month mapping
MONTHS_IT = {
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
    'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}

def parse_italian_date(text):
    """Parse date like '28-nov-2024' to '2024-11-28'."""
    match = re.match(r'(\d{1,2})-([a-z]{3})-(\d{4})', text.lower())
    if match:
        day, month_it, year = match.groups()
        month = MONTHS_IT.get(month_it, '01')
        return f"{year}-{month}-{int(day):02d}"
    return None

def parse_amount(text):
    """Parse Italian amount format: 1.234,56 -> 1234.56"""
    if not text:
        return 0.0
    clean = text.replace('.', '').replace(',', '.').replace('-', '')
    try:
        return float(clean)
    except:
        return 0.0

def extract_transactions(pdf_path):
    """Extract all transactions from PDF."""
    transactions = []
    current_date = None
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Date detection (separator row)
                date_match = re.match(r'^(\d{1,2}-[a-z]{3}-\d{4})', line.lower())
                if date_match:
                    current_date = parse_italian_date(date_match.group(1))
                    continue
                
                # Contrattazione (Trade) detection
                if line.startswith('Contrattazione'):
                    # Pattern: Contrattazione AssetName Acquista/Vendi Qty@Price Currency Amount
                    buy_match = re.search(
                        r'Contrattazione\s+(.+?)\s+Acquista\s*(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?\s*(-?[\d.,]+)?',
                        line
                    )
                    sell_match = re.search(
                        r'Contrattazione\s+(.+?)\s+Vendi\s*-?(\d+)\s*@\s*([\d.,]+)\s*(USD|EUR|CAD|GBP|DKK|HKD)?\s*(-?[\d.,]+)?',
                        line
                    )
                    
                    if buy_match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'Contrattazione',
                            'operation': 'BUY',
                            'name': buy_match.group(1).strip()[:50],
                            'quantity': float(buy_match.group(2)),
                            'price': parse_amount(buy_match.group(3)),
                            'currency': (buy_match.group(4) or 'EUR'),
                            'amount': parse_amount(buy_match.group(5)) if buy_match.group(5) else 0
                        })
                    elif sell_match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'Contrattazione',
                            'operation': 'SELL',
                            'name': sell_match.group(1).strip()[:50],
                            'quantity': float(sell_match.group(2)),
                            'price': parse_amount(sell_match.group(3)),
                            'currency': (sell_match.group(4) or 'EUR'),
                            'amount': parse_amount(sell_match.group(5)) if sell_match.group(5) else 0
                        })
                
                # Trasferimento (Deposit/Withdraw) - text has no spaces: "Trasferimentodiliquidità"
                if 'Trasferimentodiliquidit' in line:
                    # Pattern: Trasferimentodiliquidità Deposito 1.000,00
                    if 'Deposito' in line:
                        amount_match = re.search(r'Deposito\s+([\d.,]+)', line)
                        if amount_match:
                            transactions.append({
                                'page': page_num,
                                'date': current_date,
                                'type': 'Trasferimento',
                                'operation': 'DEPOSIT',
                                'name': 'Cash Deposit',
                                'quantity': 1,
                                'price': parse_amount(amount_match.group(1)),
                                'currency': 'EUR',
                                'amount': parse_amount(amount_match.group(1))
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
                                'quantity': 1,
                                'price': parse_amount(amount_match.group(1)),
                                'currency': 'EUR',
                                'amount': parse_amount(amount_match.group(1))
                            })
                
                # VenditaAllachiusura (Corporate event sell)
                if 'VenditaAllachiusura' in line:
                    match = re.search(r'VenditaAllachiusura\s*-?(\d+)\s*@\s*([\d.,]+)', line)
                    if match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'CorporateEvent',
                            'operation': 'SELL',
                            'name': 'Corporate Event',
                            'quantity': float(match.group(1)),
                            'price': parse_amount(match.group(2)),
                            'currency': 'EUR',
                            'amount': 0
                        })
                
                # AcquistoInapertura (Corporate event buy)
                if 'AcquistoInapertura' in line:
                    match = re.search(r'AcquistoInapertura\s*(\d+)\s*@\s*([\d.,]+)', line)
                    if match:
                        transactions.append({
                            'page': page_num,
                            'date': current_date,
                            'type': 'CorporateEvent',
                            'operation': 'BUY',
                            'name': 'Corporate Event',
                            'quantity': float(match.group(1)),
                            'price': parse_amount(match.group(2)),
                            'currency': 'EUR',
                            'amount': 0
                        })
    
    return transactions


def main():
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    print("🔄 PDF to CSV/Excel Conversion (pdfplumber)")
    print("=" * 60)
    print(f"Source: {pdf_path.name}")
    print()
    
    transactions = extract_transactions(str(pdf_path))
    
    print(f"\n📊 Extracted {len(transactions)} transactions")
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Show statistics
    if len(df) > 0:
        print("\nOperations breakdown:")
        print(df['operation'].value_counts().to_string())
        
        print("\nSample data:")
        print(df.head(10).to_string())
        
        # Save to CSV
        csv_path = Path("data/extracted/BG_SAXO_Transactions_Parsed.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved to: {csv_path}")
        
        # Save to Excel
        excel_path = Path("data/extracted/BG_SAXO_Transactions_Parsed.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"💾 Saved to: {excel_path}")
    else:
        print("❌ No transactions extracted!")


if __name__ == "__main__":
    main()
