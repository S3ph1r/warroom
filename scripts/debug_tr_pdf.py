"""Debug Trade Republic PDF extraction"""
import pdfplumber

pdf_path = r'D:\Download\Trade Repubblic\Estratto conto.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f'Pages: {len(pdf.pages)}')
    
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        print(f'\n{"="*60}\n=== PAGE {i+1} ===\n{"="*60}')
        print(text if text else 'No text')
        print("\n\n")
