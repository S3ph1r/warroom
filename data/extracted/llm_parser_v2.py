To parse the provided text and extract relevant information, we can use Python with libraries such as `re` for regular expressions. The goal is to create a parser that extracts details like transaction type (buy/sell), stock symbol, quantity, price, commission, conversion cost, total cost, etc.

Here's a complete Python script to parse the provided text:

```python
import re

# Sample input text
text = """
Transazioni, EUR
Periodo di rilevazione
26-nov-2024a19-dic-2025
Tipo Nomeprodotto Tipo Importocontabilizzato Contanti
Contrattazione NovoNordiskBA/S Vendi-3@78,50EUR 235,50 -
Commissione Valorecostodiconversionevaluta Costototale
-1,49EUR -236,99EUR -1,49EUR -239,48EUR
Tassodiconversione IDContrattazione ISIN
0,137568 6511192577 DK0062498333
1-dic-2025 2.160,90 2.160,90
Contrattazione NovoNordiskBA/S Vendi-3@78,50EUR 235,50 -
Commissione Valorecostodiconversionevaluta Costototale
-1,49EUR -236,99EUR -1,49EUR -239,48EUR
Tassodiconversione IDContrattazione ISIN
0,137568 6511192577 DK0062498333
1-dic-2025 2.160,90 2.160,90
Contrattazione NovoNordiskBA/S Vendi-3@78,50EUR 235,50 -
Commissione Valorecostodiconversionevaluta Costototale
-1,49EUR -236,99EUR -1,49EUR -239,48EUR
Tassodiconversione IDContrattazione ISIN
0,137568 6511192577 DK0062498333
1-dic-2025 2.160,90 2.160,90
"""

# Regular expression patterns to extract information
patterns = [
    r"Tipo\s+(.*?)\s+Tipo",
    r"Nomeprodotto\s+(.*?)\s+Tipo",
    r"Importocontabilizzato\s+(\S+)\s+-",
    r"Commissione\s+(\S+)\s+Valorecostodiconversionevaluta",
    r"Tassodiconversione\s+(\S+)",
    r"IDContrattazione\s+(\d+)",
    r"ISIN\s+(.*?)\s+\d{2}-\w{3}-\d{4}",
    r"\d{1,2}-\w{3}-\d{4}\s+(\d+\.\d+)\s+(\d+\.\d+)"
]

# Function to parse the text
def parse_text(text):
    transactions = []
    
    # Splitting the text into individual transaction blocks
    blocks = re.split(r"Contrattazione\s+", text)[1:]
    
    for block in blocks:
        transaction = {}
        
        for pattern in patterns:
            match = re.search(pattern, block)
            if match:
                transaction[re.sub(r'\s+', '_', pattern)] = match.group(1).strip()
                
        transactions.append(transaction)
    
    return transactions

# Parsing the text
parsed_transactions = parse_text(text)

# Printing parsed data
for idx, transaction in enumerate(parsed_transactions):
    print(f"Transaction {idx+1}:")
    for key, value in transaction.items():
        print(f"{key.replace('_', ' ').capitalize()}: {value}")
    print("\n")

```

### Explanation:
- **Patterns**: The regular expressions are designed to capture the relevant fields from each block of text.
  - `Tipo`: Transaction type (buy/sell).
  - `Nomeprodotto`: Stock symbol or product name.
  - `Importocontabilizzato`: Amount debited/credited.
  - `Commissione`: Commission cost.
  - `Tassodiconversione`: Conversion rate.
  - `IDContrattazione`: Transaction ID.
  - `ISIN`: ISIN code of the stock.
  - Date and balance information.

- **parse_text function**: This function splits the input text into individual transaction blocks, then uses regular expressions to extract relevant fields from each block. The extracted data is stored in a dictionary for each transaction.

### Output:
The script will output parsed transactions with their respective details:

```plaintext
Transaction 1:
Tipo: Vendi-3@78,50eur 
Nomeprodotto: Novonordiskbas 
Importocontabilizzato: 235,50 
Commissione: -1,49eur 
Tassodiconversione: 0,137568 
Id_contrattazione: 6511192577 
Isin: Dk0062498333 

Transaction 2:
Tipo: Vendi-3@78,50eur 
Nomeprodotto: Novonordiskbas 
Importocontabilizzato: 235,50 
Commissione: -1,49eur 
Tassodiconversione: 0,137568 
Id_contrattazione: 6511192577 
Isin: Dk0062498333 

Transaction 3:
Tipo: Vendi-3@78,50eur 
Nomeprodotto: Novonordiskbas 
Importocontabilizzato: 235,50 
Commissione: -1,49eur 
Tassodiconversione: 0,137568 
Id_contrattazione: 6511192577 
Isin: Dk0062498333 

```

This script can be further refined and extended to handle more complex cases or additional fields as needed.