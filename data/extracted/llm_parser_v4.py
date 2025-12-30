import re
from datetime import datetime

def extract_transactions(pdf_text):
    transactions = []
    pattern = r'(\d{1,2}-\w{3}-\d{4})\s+(\d+\.\d+|\d+)\s+(\d+\.\d+|\d+)'
    
    matches = re.findall(pattern, pdf_text)
    
    for match in matches:
        date_str, amount, balance = match
        date = datetime.strptime(date_str, '%d-%b-%Y').date()
        
        transactions.append({
            'Date': date,
            'Amount': float(amount.replace(',', '')),
            'Balance': float(balance.replace(',', ''))
        })
    
    return transactions

def extract_transaction_details(pdf_text):
    details = []
    pattern = r'Contrattazione\s+(.*?)\s+Vendi|-|\d+\@\d+\.\d+USD\s+(\d+\.\d+)\s+EUR'
    
    matches = re.findall(pattern, pdf_text)
    
    for match in matches:
        if len(match) == 2: 
            name, amount = match
            details.append({
                'Name': name.strip(),
                'Amount': float(amount.replace(',', '')),
            })
        else:
            name = match[0].strip()
            details.append({'Name': name})
    
    return details

def extract_dividends(pdf_text):
    dividends = []
    pattern = r'Dividendoincontanti\s+(\d+\.\d+)\s+EUR'
    
    matches = re.findall(pattern, pdf_text)
    
    for match in matches:
        amount = float(match.replace(',', ''))
        dividends.append({
            'Amount': amount
        })
        
    return dividends

pdf_text = """Your provided PDF text goes here"""

transactions = extract_transactions(pdf_text)
transaction_details = extract_transaction_details(pdf_text)
dividends = extract_dividends(pdf_text)

print(transactions)
print(transaction_details)
print(dividends)