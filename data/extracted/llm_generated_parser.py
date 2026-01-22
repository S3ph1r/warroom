```python
import re
from pdfplumber import PDFPlumber

def parse_bgsaxo_pdf(pdf_path: str) -> list[dict]:
    transactions = []
    
    with PDFPlumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            
            # Split the text into lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            date_pattern = re.compile(r'(\d{1,2}-[a-z]{3}-\d{4})')
            isin_pattern = re.compile(r'[A-Z0-9]{2}[A-Z0-9]{10}')
            
            for i in range(len(lines)):
                line = lines[i]
                
                # Check if the line contains a date
                match_date = date_pattern.search(line)
                if match_date:
                    date = match_date.group(1)
                    
                    # Look ahead to find transaction details
                    if 'Contrattazione' in lines[i+1]:
                        operation, name, isin, quantity_price = parse_trade(lines[i+1], lines[i+2])
                        transactions.append({
                            "date": date,
                            "operation": operation,
                            "name": name,
                            "isin": isin,
                            "quantity": quantity_price[0],
                            "price": quantity_price[1],
                            "currency": 'USD' if 'USD' in line else 'EUR',
                            "type": 'BUY' if 'Acquista' in lines[i+1] else 'SELL'
                        })
                    elif 'Trasferimentodiliquidità Deposito' in line:
                        deposit_amount = parse_deposit(lines[i])
                        transactions.append({
                            "date": date,
                            "operation": 'DEPOSIT',
                            "name": None,
                            "isin": None,
                            "quantity": None,
                            "price": None,
                            "currency": 'EUR',
                            "type": 'DEPOSIT'
                        })
                    elif 'Operazionesulcapitale' in line:
                        if 'Frazionamentoazionarioinverso' in lines[i+1]:
                            isin = parse_isin(lines[i+2])
                            transactions.append({
                                "date": date,
                                "operation": 'REVERSE_SPLIT',
                                "name": None,
                                "isin": isin,
                                "quantity": None,
                                "price": None,
                                "currency": None,
                                "type": 'REVERSE_SPLIT'
                            })
                        elif 'Distribuzionetitoliintermedi' in lines[i+1]:
                            isin = parse_isin(lines[i+2])
                            transactions.append({
                                "date": date,
                                "operation": 'DIVIDEND',
                                "name": None,
                                "isin": isin,
                                "quantity": None,
                                "price": None,
                                "currency": 'EUR',
                                "type": 'DISTRIBUTION'
                            })
    
    return transactions

def parse_trade(line, detail_line):
    operation = line.split(' ')[1]
    name = line.split(operation)[0].strip()
    isin_match = re.search(isin_pattern, detail_line)
    isin = isin_match.group(0) if isin_match else None
    quantity_price = [int(s) for s in re.findall(r'\b\d+\b', operation)]
    
    return operation, name, isin, quantity_price

def parse_deposit(line):
    deposit_amount = float(re.search(r'(\d+,\d{2})', line).group(1))
    return deposit_amount

def parse_isin(detail_line):
    isin_match = re.search(isin_pattern, detail_line)
    return isin_match.group(0) if isin_match else None


# Example usage
pdf_path = 'path_to_your_pdf.pdf'
transactions = parse_bgsaxo_pdf(pdf_path)
for transaction in transactions:
    print(transaction)
```

This Python script defines a function `parse_bgsaxo_pdf` that reads the provided PDF using pdfplumber and extracts all relevant information for each transaction type. It handles BUY, SELL, DEPOSIT, REVERSE_SPLIT, and DISTRIBUTION operations by parsing specific patterns from the text of each page in the PDF document.

The script uses regular expressions to identify dates, ISIN codes, and other key pieces of information within the text extracted from each page. The function returns a list of dictionaries where each dictionary represents an individual transaction with its date, operation type, name, ISIN code (if applicable), quantity, price, currency, and transaction type.

Please ensure you have `pdfplumber` installed in your Python environment to run this script successfully:
```bash
pip install pdfplumber
```

This solution is designed to be robust against the variations presented in the sample pages provided. Adjustments might still be necessary based on additional patterns or edge cases present in the full document.