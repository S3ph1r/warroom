import re

def parse_bgsaxo_pdf(pdf_content):
    transactions = []
    transaction_pattern = re.compile(r'Tipo\s+(.*?)\s+Nomeprodotto\s+(.*?)\s+Tipo\s+\d+\.\d+\s+(\-?\d{1,3}(?:\,\d{2})?)')
    
    for match in transaction_pattern.finditer(pdf_content):
        transaction_type = match.group(1).strip()
        product_name = match.group(2).strip()
        amount = float(match.group(3).replace(',', '.'))
        
        transactions.append({
            'type': transaction_type,
            'product': product_name,
            'amount': amount
        })
    
    return transactions

def main():
    pdf_content = """
Transazioni, EUR
Periodo di rendicontazione
26-nov-2024a19-dic-2025
Tipo Nomeprodotto Tipo Importocontabilizzato Contanti
Contrattazione NovoNordiskBA/S Acquista 4@319,10DKK -172,66 -
Commissione Valorenegoziato Costodiconversionevaluta Costototale
-1,34EUR -171,32EUR -0,43 -1,77EUR
Tassodiconversione IDcontrattazione ISIN
0,134218 6513054071 DK0062498333
11-dic-2025 178,74 2.339,64
Contrattazione OculusInc. Vendi -7000@0,05CAD 178,74 -
Commissione Valorenegoziato Costodiconversionevaluta Costototale
-15,41EUR 194,15EUR -0,45 -15,90EUR
Tassodiconversione IDcontrattazione ISIN
0,616359 6511202189 US67575Y1091
10-dic-2025 2.000,23 2.160,90
Trasferimentodiliquidità Deposito 2.000,00 -
Commento DepositType Tassodiconversione Importoincontanti
/OCMT/EUR2000,/19807401 External 1,000000 2.000,00EUR
"""
    transactions = parse_bgsaxo_pdf(pdf_content)
    print(transactions)

if __name__ == "__main__":
    main()